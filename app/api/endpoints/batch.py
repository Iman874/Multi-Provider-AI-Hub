"""
Batch endpoints — Process multiple prompts/texts in a single request.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_batch_service
from app.schemas.requests import BatchGenerateRequest, BatchEmbeddingRequest
from app.schemas.responses import BatchGenerateResponse, BatchEmbeddingResponse
from app.services.batch_service import BatchService

router = APIRouter()


@router.post(
    "/batch/generate",
    response_model=BatchGenerateResponse,
    summary="Batch text generation",
    description="Process multiple prompts in a single request with concurrent execution. "
    "Each item is processed independently — partial failures are captured per-item.",
)
async def batch_generate(
    request: BatchGenerateRequest,
    batch_service: BatchService = Depends(get_batch_service),
) -> BatchGenerateResponse:
    """Batch generate text for multiple prompts."""
    return await batch_service.generate_batch(request)


@router.post(
    "/batch/embedding",
    response_model=BatchEmbeddingResponse,
    summary="Batch embedding generation",
    description="Generate embeddings for multiple texts in a single request.",
)
async def batch_embedding(
    request: BatchEmbeddingRequest,
    batch_service: BatchService = Depends(get_batch_service),
) -> BatchEmbeddingResponse:
    """Batch generate embeddings for multiple texts."""
    return await batch_service.embedding_batch(request)
