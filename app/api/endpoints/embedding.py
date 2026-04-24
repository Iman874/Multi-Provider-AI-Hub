"""
Embedding endpoint — Generate vector embeddings from text.

Delegates all logic to GeneratorService.
This endpoint contains NO business logic.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_generator_service
from app.schemas.requests import EmbeddingRequest
from app.schemas.responses import EmbeddingResponse, ErrorResponse
from app.services.generator import GeneratorService

router = APIRouter()


@router.post(
    "/embedding",
    response_model=EmbeddingResponse,
    summary="Generate text embedding",
    description="Generate a vector embedding from input text using the specified "
    "provider and embedding model. The model must support embedding capability.",
    responses={
        400: {"model": ErrorResponse, "description": "Model doesn't support embedding"},
        404: {"model": ErrorResponse, "description": "Provider or model not found"},
        502: {"model": ErrorResponse, "description": "Provider connection error"},
        504: {"model": ErrorResponse, "description": "Provider timeout"},
    },
)
async def create_embedding(
    request: EmbeddingRequest,
    service: GeneratorService = Depends(get_generator_service),
) -> EmbeddingResponse:
    """
    Generate embedding vector from text.

    The model must have embedding capability (e.g. nomic-embed-text, text-embedding-004).
    Text generation models (e.g. llama3.2) will return a 400 error.
    """
    return await service.embedding(request)
