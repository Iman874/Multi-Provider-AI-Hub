"""
Abstract base provider for AI Generative Core.

All AI providers (Ollama, Gemini, etc.) MUST inherit from this class
and implement all abstract methods. This ensures a consistent interface
across providers, enabling the service layer to work with any provider
without knowing its implementation details.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional


class BaseProvider(ABC):
    """
    Abstract contract for all AI providers.

    Adding a new provider requires:
    1. Create a new class extending BaseProvider
    2. Implement all abstract methods
    3. Register in provider factory
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique provider identifier.

        Returns:
            Provider name string, e.g. "ollama", "gemini"
        """
        ...

    @abstractmethod
    async def generate(
        self,
        model: str,
        prompt: str,
        images: Optional[list[str]] = None,
    ) -> dict:
        """
        Generate text or multimodal response.

        Args:
            model: Model identifier (e.g. "llama3.2", "gemini-2.5-pro")
            prompt: Text input/prompt
            images: Optional list of base64-encoded images

        Returns:
            Normalized dict with keys:
            - output (str): Generated text
            - model (str): Model used
            - provider (str): Provider name
            - usage (dict | None): Token usage stats
            - metadata (dict | None): Additional info (e.g. duration)
        """
        ...

    @abstractmethod
    async def stream(
        self,
        model: str,
        prompt: str,
        images: Optional[list[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream generated tokens one at a time.

        Args:
            model: Model identifier
            prompt: Text input/prompt
            images: Optional list of base64-encoded images

        Yields:
            Individual token strings as they are generated.
        """
        ...

    @abstractmethod
    async def embedding(
        self,
        model: str,
        input_text: str,
    ) -> list[float]:
        """
        Generate embedding vector from text.

        Args:
            model: Embedding model identifier
            input_text: Text to embed

        Returns:
            List of floats representing the embedding vector.
        """
        ...

    @abstractmethod
    def supports_image(self, model: str) -> bool:
        """
        Check if a specific model supports image/multimodal input.

        Args:
            model: Model identifier to check

        Returns:
            True if the model accepts image input.
        """
        ...

    @abstractmethod
    async def fetch_models(self) -> list:
        """
        Fetch available models directly from the provider's API.

        Returns:
            List of ModelCapability objects.
        """
        ...

    async def close(self) -> None:
        """
        Cleanup provider resources (HTTP clients, connections, etc).

        Override in subclass if cleanup is needed.
        Default implementation is a no-op.
        """
        pass
