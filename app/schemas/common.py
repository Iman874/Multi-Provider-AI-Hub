"""
Shared types and enums used across all schemas.

ProviderEnum defines the supported AI providers and is used
in every request schema for input validation.
"""

from enum import Enum


class ProviderEnum(str, Enum):
    """
    Supported AI providers.

    Used as the `provider` field in all request schemas.
    Pydantic will automatically validate that only these values are accepted.
    """

    OLLAMA = "ollama"
    GEMINI = "gemini"
    NVIDIA = "nvidia"
    AUTO = "auto"
