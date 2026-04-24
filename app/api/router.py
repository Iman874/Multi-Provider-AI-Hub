"""
Central API router that combines all endpoint routers.
"""

from fastapi import APIRouter, Depends

from app.api.endpoints import models, generate, stream, embedding, chat, cache, batch
from app.core.auth import verify_gateway_token

api_router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(verify_gateway_token)],
)

# --- Register endpoint routers ---
api_router.include_router(models.router, tags=["Models"])
api_router.include_router(generate.router, tags=["Generation"])
api_router.include_router(stream.router, tags=["Streaming"])
api_router.include_router(embedding.router, tags=["Embedding"])
api_router.include_router(chat.router, tags=["Chat"])
api_router.include_router(cache.router, tags=["Cache"])
api_router.include_router(batch.router, tags=["Batch"])
