"""
Batch Processing Service — Concurrent multi-item generation and embedding.

Orchestrates parallel processing of multiple prompts/texts in a single
request, with configurable concurrency limits via asyncio.Semaphore.
"""

import asyncio
from loguru import logger

from app.core.exceptions import BatchTooLargeError, ModelCapabilityError
from app.schemas.requests import (
    BatchGenerateRequest,
    BatchGenerateItem,
    BatchEmbeddingRequest,
    GenerateRequest,
    EmbeddingRequest,
)
from app.schemas.responses import (
    BatchGenerateResult,
    BatchGenerateResponse,
    BatchEmbeddingResult,
    BatchEmbeddingResponse,
)
from app.services.generator import GeneratorService


class BatchService:
    """
    Orchestrator for batch AI operations.

    Processes multiple items concurrently with a semaphore-based
    concurrency limit. Each item is delegated to GeneratorService,
    which handles caching, validation, and provider calls.
    """

    def __init__(
        self,
        generator: GeneratorService,
        max_size: int = 20,
        concurrency: int = 5,
    ):
        """
        Initialize BatchService.

        Args:
            generator: GeneratorService instance for individual item processing.
            max_size: Maximum number of items allowed per batch request.
            concurrency: Maximum concurrent provider calls within a batch.
        """
        self._generator = generator
        self._max_size = max_size
        self._concurrency = concurrency
        self._semaphore = asyncio.Semaphore(concurrency)
        logger.info(
            "BatchService initialized: max_size={max_size}, concurrency={concurrency}",
            max_size=max_size,
            concurrency=concurrency,
        )

    async def generate_batch(
        self, request: BatchGenerateRequest
    ) -> BatchGenerateResponse:
        """
        Process a batch of generation requests concurrently.

        Flow:
        1. Validate batch size against max_size
        2. Validate provider & model ONCE (fail fast before processing)
        3. Process all items concurrently via asyncio.gather
        4. Build aggregate response with per-item results

        Args:
            request: Validated BatchGenerateRequest with list of items.

        Returns:
            BatchGenerateResponse with per-item results.

        Raises:
            BatchTooLargeError: If len(items) > max_size.
            ProviderNotFoundError: If provider doesn't exist.
            ModelNotFoundError: If model doesn't exist.
        """
        # 1. Validate batch size
        if len(request.items) > self._max_size:
            raise BatchTooLargeError(
                actual=len(request.items),
                maximum=self._max_size,
            )

        # 2. Validate provider & model ONCE (fail fast)
        self._generator._get_provider(request.provider.value)
        self._generator._registry.get_model(
            provider=request.provider.value,
            name=request.model,
        )

        # 3. Process all items concurrently
        tasks = [
            self._process_generate_item(i, item, request.provider, request.model)
            for i, item in enumerate(request.items)
        ]
        results = await asyncio.gather(*tasks)

        # 4. Build aggregate response
        succeeded = sum(1 for r in results if r.status == "success")
        return BatchGenerateResponse(
            provider=request.provider.value,
            model=request.model,
            total=len(results),
            succeeded=succeeded,
            failed=len(results) - succeeded,
            results=sorted(results, key=lambda r: r.index),
        )

    async def _process_generate_item(
        self,
        index: int,
        item: BatchGenerateItem,
        provider: "ProviderEnum",
        model: str,
    ) -> BatchGenerateResult:
        """
        Process a single generate item with semaphore-based concurrency.

        Wraps GeneratorService.generate() with error handling.
        On success: returns result with output, usage, and cached flag.
        On failure: returns result with error message.
        """
        async with self._semaphore:
            try:
                request = GenerateRequest(
                    provider=provider,
                    model=model,
                    input=item.input,
                    images=item.images,
                )
                response = await self._generator.generate(request)

                return BatchGenerateResult(
                    index=index,
                    status="success",
                    output=response.output,
                    usage=response.usage,
                    cached=(
                        response.metadata.get("cached", False)
                        if response.metadata
                        else False
                    ),
                )
            except Exception as e:
                logger.warning(
                    "Batch generate item {idx} failed: {err}",
                    idx=index,
                    err=str(e),
                )
                return BatchGenerateResult(
                    index=index,
                    status="error",
                    error=str(e),
                )

    async def embedding_batch(
        self, request: BatchEmbeddingRequest
    ) -> BatchEmbeddingResponse:
        """
        Process a batch of embedding requests concurrently.

        Same flow as generate_batch() but for embeddings.

        Args:
            request: Validated BatchEmbeddingRequest with list of texts.

        Returns:
            BatchEmbeddingResponse with per-item results.

        Raises:
            BatchTooLargeError: If len(inputs) > max_size.
            ProviderNotFoundError: If provider doesn't exist.
            ModelNotFoundError: If model doesn't exist.
            ModelCapabilityError: If model doesn't support embedding.
        """
        # 1. Validate batch size
        if len(request.inputs) > self._max_size:
            raise BatchTooLargeError(
                actual=len(request.inputs),
                maximum=self._max_size,
            )

        # 2. Validate provider & model ONCE (fail fast)
        self._generator._get_provider(request.provider.value)
        model_info = self._generator._registry.get_model(
            provider=request.provider.value,
            name=request.model,
        )

        # Also validate embedding capability upfront
        if not model_info.supports_embedding:
            raise ModelCapabilityError(
                model=request.model,
                capability="embedding",
            )

        # 3. Process all items concurrently
        tasks = [
            self._process_embedding_item(i, text, request.provider, request.model)
            for i, text in enumerate(request.inputs)
        ]
        results = await asyncio.gather(*tasks)

        # 4. Build aggregate response
        succeeded = sum(1 for r in results if r.status == "success")
        return BatchEmbeddingResponse(
            provider=request.provider.value,
            model=request.model,
            total=len(results),
            succeeded=succeeded,
            failed=len(results) - succeeded,
            results=sorted(results, key=lambda r: r.index),
        )

    async def _process_embedding_item(
        self,
        index: int,
        text: str,
        provider: "ProviderEnum",
        model: str,
    ) -> BatchEmbeddingResult:
        """
        Process a single embedding item with semaphore-based concurrency.

        Wraps GeneratorService.embedding() with error handling.
        """
        async with self._semaphore:
            try:
                request = EmbeddingRequest(
                    provider=provider,
                    model=model,
                    input=text,
                )
                response = await self._generator.embedding(request)

                return BatchEmbeddingResult(
                    index=index,
                    status="success",
                    embedding=response.embedding,
                    cached=False,
                )
            except Exception as e:
                logger.warning(
                    "Batch embedding item {idx} failed: {err}",
                    idx=index,
                    err=str(e),
                )
                return BatchEmbeddingResult(
                    index=index,
                    status="error",
                    error=str(e),
                )
