"""
Unit tests for BatchService.

Tests cover: batch success, partial failure, size validation,
cache integration, concurrency limit, and provider/model validation.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.core.exceptions import (
    BatchTooLargeError,
    ProviderNotFoundError,
    ModelNotFoundError,
)
from app.schemas.requests import BatchGenerateRequest, BatchGenerateItem, BatchEmbeddingRequest
from app.schemas.responses import GenerateResponse, UsageInfo, EmbeddingResponse
from app.services.batch_service import BatchService


@pytest.fixture
def mock_generator():
    """Create a mock GeneratorService."""
    gen = MagicMock()

    # Mock _get_provider (returns a mock provider — validation passes)
    gen._get_provider.return_value = MagicMock()

    # Mock _registry.get_model (returns a model with capabilities)
    mock_model = MagicMock()
    mock_model.supports_embedding = True
    mock_model.supports_text = True
    mock_model.supports_image = False
    gen._registry.get_model.return_value = mock_model

    # Default mock for generate — returns a GenerateResponse
    gen.generate = AsyncMock(return_value=GenerateResponse(
        output="Mock output",
        provider="ollama",
        model="gemma4:e2b",
        usage=UsageInfo(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        metadata={"cached": False},
    ))

    # Default mock for embedding — returns an EmbeddingResponse
    gen.embedding = AsyncMock(return_value=EmbeddingResponse(
        embedding=[0.1, 0.2, 0.3],
        provider="ollama",
        model="qwen3-embedding:0.6b",
    ))

    return gen


@pytest.fixture
def batch_service(mock_generator):
    """BatchService with max_size=5 and concurrency=2."""
    return BatchService(
        generator=mock_generator,
        max_size=5,
        concurrency=2,
    )


@pytest.mark.asyncio
async def test_batch_generate_success(batch_service, mock_generator):
    """3 items, all succeed → succeeded=3, failed=0."""
    request = BatchGenerateRequest(
        provider="ollama",
        model="gemma4:e2b",
        items=[
            BatchGenerateItem(input="Prompt 1"),
            BatchGenerateItem(input="Prompt 2"),
            BatchGenerateItem(input="Prompt 3"),
        ],
    )
    response = await batch_service.generate_batch(request)

    assert response.total == 3
    assert response.succeeded == 3
    assert response.failed == 0
    assert response.provider == "ollama"
    assert response.model == "gemma4:e2b"
    assert len(response.results) == 3
    for r in response.results:
        assert r.status == "success"
        assert r.output == "Mock output"
    assert mock_generator.generate.call_count == 3


@pytest.mark.asyncio
async def test_batch_embedding_success(batch_service, mock_generator):
    """3 texts, all succeed → succeeded=3, failed=0."""
    request = BatchEmbeddingRequest(
        provider="ollama",
        model="qwen3-embedding:0.6b",
        inputs=["Text 1", "Text 2", "Text 3"],
    )
    response = await batch_service.embedding_batch(request)

    assert response.total == 3
    assert response.succeeded == 3
    assert response.failed == 0
    assert len(response.results) == 3
    for r in response.results:
        assert r.status == "success"
        assert r.embedding == [0.1, 0.2, 0.3]
    assert mock_generator.embedding.call_count == 3


@pytest.mark.asyncio
async def test_batch_partial_failure(batch_service, mock_generator):
    """1 fails, 2 succeed → succeeded=2, failed=1."""
    call_count = 0

    async def mock_generate(request):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise Exception("Provider timeout after 30s")
        return GenerateResponse(
            output="OK",
            provider="ollama",
            model="gemma4:e2b",
            metadata={"cached": False},
        )

    mock_generator.generate = mock_generate

    request = BatchGenerateRequest(
        provider="ollama",
        model="gemma4:e2b",
        items=[
            BatchGenerateItem(input="Prompt 1"),
            BatchGenerateItem(input="Prompt 2"),
            BatchGenerateItem(input="Prompt 3"),
        ],
    )
    response = await batch_service.generate_batch(request)

    assert response.total == 3
    assert response.succeeded == 2
    assert response.failed == 1

    # Find the failed item
    failed = [r for r in response.results if r.status == "error"]
    assert len(failed) == 1
    assert "timeout" in failed[0].error.lower()

    success = [r for r in response.results if r.status == "success"]
    assert len(success) == 2


@pytest.mark.asyncio
async def test_batch_too_large(batch_service):
    """10 items with max_size=5 → BatchTooLargeError."""
    request = BatchGenerateRequest(
        provider="ollama",
        model="gemma4:e2b",
        items=[BatchGenerateItem(input=f"Prompt {i}") for i in range(10)],
    )

    with pytest.raises(BatchTooLargeError) as exc_info:
        await batch_service.generate_batch(request)

    assert exc_info.value.actual == 10
    assert exc_info.value.maximum == 5
    assert exc_info.value.code == "BATCH_TOO_LARGE"


@pytest.mark.asyncio
async def test_batch_single_item(batch_service, mock_generator):
    """1 item batch works same as individual request."""
    request = BatchGenerateRequest(
        provider="ollama",
        model="gemma4:e2b",
        items=[BatchGenerateItem(input="Single prompt")],
    )
    response = await batch_service.generate_batch(request)

    assert response.total == 1
    assert response.succeeded == 1
    assert response.failed == 0
    assert response.results[0].output == "Mock output"
    assert mock_generator.generate.call_count == 1


@pytest.mark.asyncio
async def test_batch_cache_integration(batch_service, mock_generator):
    """Cached items returned with cached=True."""
    mock_generator.generate = AsyncMock(return_value=GenerateResponse(
        output="Cached output",
        provider="ollama",
        model="gemma4:e2b",
        metadata={"cached": True},
    ))

    request = BatchGenerateRequest(
        provider="ollama",
        model="gemma4:e2b",
        items=[BatchGenerateItem(input="Cached prompt")],
    )
    response = await batch_service.generate_batch(request)

    assert response.results[0].cached is True
    assert response.results[0].output == "Cached output"


@pytest.mark.asyncio
async def test_batch_concurrency_limit(mock_generator):
    """Verify semaphore limits concurrent calls to concurrency value."""
    max_concurrent = 0
    current_concurrent = 0
    lock = asyncio.Lock()

    async def slow_generate(request):
        nonlocal max_concurrent, current_concurrent
        async with lock:
            current_concurrent += 1
            if current_concurrent > max_concurrent:
                max_concurrent = current_concurrent
        await asyncio.sleep(0.05)
        async with lock:
            current_concurrent -= 1
        return GenerateResponse(
            output="OK",
            provider="ollama",
            model="gemma4:e2b",
            metadata={"cached": False},
        )

    mock_generator.generate = slow_generate

    # concurrency=2, so max 2 concurrent
    service = BatchService(generator=mock_generator, max_size=10, concurrency=2)

    request = BatchGenerateRequest(
        provider="ollama",
        model="gemma4:e2b",
        items=[BatchGenerateItem(input=f"Prompt {i}") for i in range(5)],
    )
    response = await service.generate_batch(request)

    assert response.succeeded == 5
    assert max_concurrent <= 2


@pytest.mark.asyncio
async def test_batch_provider_validation(batch_service, mock_generator):
    """Invalid provider → ProviderNotFoundError before any item processing."""
    mock_generator._get_provider.side_effect = ProviderNotFoundError("invalid")

    request = BatchGenerateRequest(
        provider="ollama",
        model="gemma4:e2b",
        items=[BatchGenerateItem(input="Prompt")],
    )

    with pytest.raises(ProviderNotFoundError):
        await batch_service.generate_batch(request)

    # generate() should NOT have been called
    mock_generator.generate.assert_not_called()


@pytest.mark.asyncio
async def test_batch_model_validation(batch_service, mock_generator):
    """Invalid model → ModelNotFoundError before any item processing."""
    mock_generator._registry.get_model.side_effect = ModelNotFoundError("ollama", "fake")

    request = BatchGenerateRequest(
        provider="ollama",
        model="fake",
        items=[BatchGenerateItem(input="Prompt")],
    )

    with pytest.raises(ModelNotFoundError):
        await batch_service.generate_batch(request)

    mock_generator.generate.assert_not_called()


def test_batch_empty_rejected():
    """Empty items list rejected by Pydantic validation (min_length=1)."""
    with pytest.raises(ValidationError):
        BatchGenerateRequest(
            provider="ollama",
            model="gemma4:e2b",
            items=[],
        )
