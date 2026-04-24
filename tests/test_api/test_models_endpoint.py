"""
API tests for GET /api/v1/models.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_health_checker, get_model_registry
from app.api.endpoints.models import router
from app.services.health_checker import HealthChecker
from app.services.model_registry import ModelCapability, ModelRegistry


def test_models_endpoint_includes_supports_reasoning():
    """Models endpoint returns reasoning capability in the response payload."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    registry = ModelRegistry()
    registry.register(
        ModelCapability(
            name="gemini-2.5-pro",
            provider="gemini",
            supports_text=True,
            supports_image=True,
            supports_embedding=False,
            supports_streaming=True,
            supports_reasoning=True,
        )
    )

    health_checker = HealthChecker(providers={})

    app.dependency_overrides[get_model_registry] = lambda: registry
    app.dependency_overrides[get_health_checker] = lambda: health_checker

    client = TestClient(app)
    response = client.get("/api/v1/models")

    assert response.status_code == 200
    assert response.json() == [
        {
            "name": "gemini-2.5-pro",
            "provider": "gemini",
            "supports_text": True,
            "supports_image": True,
            "supports_embedding": False,
            "supports_reasoning": True,
            "available": True,
        }
    ]
