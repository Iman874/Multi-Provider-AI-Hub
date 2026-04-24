"""
Streaming endpoint — Server-Sent Events (SSE) for token-by-token generation.

Uses sse-starlette to send EventSourceResponse.
All validation happens BEFORE streaming starts, so errors
return proper JSON responses (not broken SSE streams).
"""

import json

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse
from loguru import logger

from app.api.dependencies import get_generator_service
from app.schemas.requests import StreamRequest
from app.schemas.responses import ErrorResponse
from app.services.generator import GeneratorService

router = APIRouter()


@router.post(
    "/stream",
    summary="Stream generated tokens via SSE",
    description="Send a prompt and receive AI-generated tokens one at a time "
    "via Server-Sent Events (SSE). Each event contains a JSON object "
    'with a "token" field. The stream ends with a `[DONE]` marker.',
    responses={
        400: {"model": ErrorResponse, "description": "Capability not supported"},
        404: {"model": ErrorResponse, "description": "Provider or model not found"},
        502: {"model": ErrorResponse, "description": "Provider connection error"},
        504: {"model": ErrorResponse, "description": "Provider timeout"},
    },
)
async def stream_generate(
    request: StreamRequest,
    service: GeneratorService = Depends(get_generator_service),
):
    """
    Stream AI-generated tokens via Server-Sent Events.

    SSE output format:
        data: {"token": "Hello"}
        data: {"token": " world"}
        data: {"token": "!"}
        data: [DONE]

    Client consumption (JavaScript):
        const source = new EventSource('/api/v1/stream', ...);
        source.onmessage = (e) => {
            if (e.data === '[DONE]') { source.close(); return; }
            const { token } = JSON.parse(e.data);
            // append token to UI
        };
    """

    async def event_generator():
        """
        Internal generator that yields SSE-formatted events.

        Validation errors from GeneratorService are raised before
        this generator starts, so they result in proper JSON error
        responses via the global exception handler.
        """
        try:
            async for token in service.stream(request):
                yield {
                    "data": json.dumps({"token": token}),
                }
        except Exception as e:
            # Mid-stream error — log and send error event
            logger.error(
                "Stream error: {error}",
                error=str(e),
            )
            yield {
                "data": json.dumps({
                    "error": str(e),
                    "code": getattr(e, "code", "STREAM_ERROR"),
                }),
            }

        # Send termination marker
        yield {"data": "[DONE]"}

    return EventSourceResponse(event_generator())
