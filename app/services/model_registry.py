"""
Model Registry for AI Generative Core.

Provides a central catalog of all available AI models and their capabilities.
Models are registered at startup and queried by the GeneratorService
to validate requests before routing them to providers.
"""

from dataclasses import dataclass

from loguru import logger

from app.core.exceptions import ModelNotFoundError


@dataclass
class ModelCapability:
    """
    Metadata and capabilities of a single AI model.

    Attributes:
        name: Model identifier (e.g. "llama3.2", "gemini-2.0-flash")
        provider: Provider that hosts this model ("ollama", "gemini")
        supports_text: Whether the model can generate text
        supports_image: Whether the model accepts image input (multimodal)
        supports_embedding: Whether the model can generate embeddings
        supports_reasoning: Whether the model supports explicit reasoning mode
    """

    name: str
    provider: str
    supports_text: bool = True
    supports_image: bool = False
    supports_embedding: bool = False
    supports_streaming: bool = True
    supports_reasoning: bool = False


class ModelRegistry:
    """
    Central catalog of all available models.

    Models are registered at startup via register() or register_defaults().
    The registry is queried by GeneratorService to:
    1. Check if a model exists
    2. Validate model capabilities (image support, embedding support)
    3. List available models for the GET /models endpoint
    """

    def __init__(self):
        self._models: dict[str, ModelCapability] = {}

    def _make_key(self, provider: str, name: str) -> str:
        """Generate unique registry key from provider and model name."""
        return f"{provider}:{name}"

    def register(self, model: ModelCapability) -> None:
        """
        Register a model in the catalog.

        Args:
            model: ModelCapability instance to register.
        """
        key = self._make_key(model.provider, model.name)
        self._models[key] = model
        logger.debug(
            "Registered model: {key}",
            key=key,
        )

    def get_model(self, provider: str, name: str) -> ModelCapability:
        """
        Look up a model by provider and name.

        Args:
            provider: Provider identifier (e.g. "ollama")
            name: Model name (e.g. "llama3.2")

        Returns:
            ModelCapability for the requested model.

        Raises:
            ModelNotFoundError: If the model is not registered.
        """
        key = self._make_key(provider, name)
        model = self._models.get(key)
        if model is None:
            raise ModelNotFoundError(provider=provider, model=name)
        return model

    def list_models(self, provider: str | None = None) -> list[ModelCapability]:
        """
        List all registered models, optionally filtered by provider.

        Args:
            provider: If provided, only return models from this provider.

        Returns:
            List of ModelCapability instances.
        """
        models = list(self._models.values())
        if provider:
            models = [m for m in models if m.provider == provider]
        return models

    def clear(self) -> None:
        """Clear all registered models."""
        self._models.clear()
