"""
Request schemas for AI Generative Core API.

These Pydantic models define and validate the structure of incoming
request bodies for all API endpoints.
"""

from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ProviderEnum


def _validate_auto_model_selection(provider: ProviderEnum, model: str) -> None:
    """
    Ensure the special "auto" model is only used with the auto provider.

    Args:
        provider: Selected provider enum from the request schema.
        model: Selected model string from the request schema.

    Returns:
        None.

    Raises:
        ValueError: If model="auto" is used with a non-auto provider.
    """
    if provider != ProviderEnum.AUTO and model == "auto":
        raise ValueError("model must be specified unless provider='auto'")


class GenerateRequest(BaseModel):
    """
    Request body for POST /generate.

    Supports text-only and multimodal (text + images) generation.
    If images are provided, the model must support multimodal input.
    """

    provider: ProviderEnum = Field(
        ...,
        description="AI provider to use",
        examples=["auto", "ollama", "gemini"],
    )
    model: str = Field(
        default="auto",
        description="Model name or 'auto' for smart routing",
        examples=["auto", "llama3.2", "gemini-2.5-pro"],
    )
    input: str = Field(
        ...,
        min_length=1,
        description="Text prompt for generation",
    )
    images: Optional[list[str]] = Field(
        default=None,
        description="Optional list of base64-encoded images or image URLs for multimodal input",
    )
    stream: bool = Field(
        default=False,
        description="If true, use POST /stream endpoint instead for SSE streaming",
    )

    @model_validator(mode="after")
    def validate_model_selection(self) -> "GenerateRequest":
        """
        Validate the provider/model combination for generate requests.

        Returns:
            The validated GenerateRequest instance.
        """
        _validate_auto_model_selection(self.provider, self.model)
        return self


class StreamRequest(BaseModel):
    """
    Request body for POST /stream.

    Same as GenerateRequest but without the stream flag,
    since streaming is implicit for this endpoint.
    """

    provider: ProviderEnum = Field(
        ...,
        description="AI provider to use",
        examples=["auto", "ollama", "gemini"],
    )
    model: str = Field(
        default="auto",
        description="Model name or 'auto' for smart routing",
        examples=["auto", "llama3.2", "gemini-2.5-pro"],
    )
    input: str = Field(
        ...,
        min_length=1,
        description="Text prompt for generation",
    )
    images: Optional[list[str]] = Field(
        default=None,
        description="Optional list of base64-encoded images for multimodal input",
    )

    @model_validator(mode="after")
    def validate_model_selection(self) -> "StreamRequest":
        """
        Validate the provider/model combination for stream requests.

        Returns:
            The validated StreamRequest instance.
        """
        _validate_auto_model_selection(self.provider, self.model)
        return self


class EmbeddingRequest(BaseModel):
    """
    Request body for POST /embedding.

    Generates a vector embedding from the input text.
    The model must support embedding capability.
    """

    provider: ProviderEnum = Field(
        ...,
        description="AI provider to use",
        examples=["auto", "ollama", "gemini"],
    )
    model: str = Field(
        default="auto",
        description="Embedding model name or 'auto' for smart routing",
        examples=["auto", "nomic-embed-text", "text-embedding-004"],
    )
    input: str = Field(
        ...,
        min_length=1,
        description="Text to generate embedding for",
    )

    @model_validator(mode="after")
    def validate_model_selection(self) -> "EmbeddingRequest":
        """
        Validate the provider/model combination for embedding requests.

        Returns:
            The validated EmbeddingRequest instance.
        """
        _validate_auto_model_selection(self.provider, self.model)
        return self


class ChatRequest(BaseModel):
    """
    Request body for POST /chat.

    Supports multi-turn conversation with server-side history.
    If session_id is null, a new session is created.
    If session_id is provided, the existing session is continued.
    """

    provider: ProviderEnum = Field(
        ...,
        description="AI provider to use",
        examples=["auto", "ollama", "gemini"],
    )
    model: str = Field(
        default="auto",
        description="Model name or 'auto' for smart routing",
        examples=["auto", "llama3.2", "gemini-2.5-pro"],
    )
    message: str = Field(
        ...,
        min_length=1,
        description="User message for this turn",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Existing session ID to continue. Null = create new session",
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="System prompt (only used when creating a new session)",
    )

    @model_validator(mode="after")
    def validate_model_selection(self) -> "ChatRequest":
        """
        Validate the provider/model combination for chat requests.

        Returns:
            The validated ChatRequest instance.
        """
        _validate_auto_model_selection(self.provider, self.model)
        return self


class BatchGenerateItem(BaseModel):
    """Single item in a batch generate request."""

    input: str = Field(
        ...,
        min_length=1,
        description="Text prompt for generation",
    )
    images: Optional[list[str]] = Field(
        default=None,
        description="Optional list of base64-encoded images for multimodal input",
    )


class BatchGenerateRequest(BaseModel):
    """Request body for POST /batch/generate."""

    provider: ProviderEnum = Field(
        ...,
        description="AI provider to use",
        examples=["ollama", "gemini"],
    )
    model: str = Field(
        ...,
        description="Model name",
        examples=["llama3.2", "gemini-2.5-pro"],
    )
    items: list[BatchGenerateItem] = Field(
        ...,
        min_length=1,
        description="List of prompts to generate",
    )


class BatchEmbeddingRequest(BaseModel):
    """Request body for POST /batch/embedding."""

    provider: ProviderEnum = Field(
        ...,
        description="AI provider to use",
        examples=["ollama", "gemini"],
    )
    model: str = Field(
        ...,
        description="Embedding model name",
        examples=["nomic-embed-text", "text-embedding-004"],
    )
    inputs: list[str] = Field(
        ...,
        min_length=1,
        description="List of texts to embed",
    )
