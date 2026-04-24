"""
Generate endpoint — Text and multimodal AI generation.

Delegates all logic to GeneratorService.
This endpoint contains NO business logic.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_generator_service
from app.schemas.requests import GenerateRequest
from app.schemas.responses import ErrorResponse, GenerateResponse
from app.services.generator import GeneratorService

router = APIRouter()


@router.post(
    "/generate",
    response_model=GenerateResponse,
    summary="Generate text or multimodal response",
    description="Send a prompt to an AI provider and receive a generated response. "
    "Supports text-only and multimodal (text + images) input.",
    responses={
        400: {"model": ErrorResponse, "description": "Capability not supported"},
        404: {"model": ErrorResponse, "description": "Provider or model not found"},
        502: {"model": ErrorResponse, "description": "Provider connection error"},
        504: {"model": ErrorResponse, "description": "Provider timeout"},
    },
)
async def generate(
    request: GenerateRequest,
    service: GeneratorService = Depends(get_generator_service),
) -> GenerateResponse:
    """
    Generate AI response from the specified provider and model.

    The request is routed to the appropriate provider (Ollama, Gemini)
    after validating the model exists and supports the requested capabilities.
    """
    return await service.generate(request)
