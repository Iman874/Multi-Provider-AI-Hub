"""
Reasoning capability detection helpers.

Provides conservative provider-specific rules for determining whether
an exposed model should be marked as supporting explicit reasoning mode.
"""

from collections.abc import Iterable
from typing import Any


OLLAMA_REASONING_KEYWORDS = (
    "thinking",
    "reasoning",
    "think",
    "qwq",
    "deepseek-r1",
    "r1",
)

OLLAMA_REASONING_FAMILIES = {
    "qwen3",
    "qwen3-next",
    "qwen3-coder",
    "qwq",
    "deepseek-r1",
}

NVIDIA_REASONING_MODEL_IDS = {
    "nvidia/nvidia-nemotron-nano-9b-v2",
    "nvidia/nemotron-3-nano-30b-a3b",
    "qwen/qwen3-next-80b-a3b-thinking",
}


def _normalize_string_list(values: Any) -> list[str]:
    """
    Normalize model metadata values into lowercase string tokens.

    Args:
        values: Provider metadata field that may be scalar, list, or nested.

    Returns:
        Lowercased string tokens extracted from the input.
    """
    if values is None:
        return []

    if isinstance(values, str):
        return [values.lower()]

    if isinstance(values, Iterable):
        normalized: list[str] = []
        for value in values:
            normalized.extend(_normalize_string_list(value))
        return normalized

    return [str(values).lower()]


def detect_ollama_reasoning(
    model_name: str,
    model_details: dict[str, Any] | None = None,
) -> bool:
    """
    Detect Ollama reasoning support from show metadata plus name heuristic.

    Args:
        model_name: Exposed Ollama model name.
        model_details: Optional payload returned by POST /api/show.

    Returns:
        True when the model is likely to support reasoning mode.
    """
    lowered_name = model_name.lower()

    if any(keyword in lowered_name for keyword in OLLAMA_REASONING_KEYWORDS):
        return True

    if not model_details:
        return False

    details = {str(key).lower(): value for key, value in model_details.items()}
    capabilities = _normalize_string_list(details.get("capabilities"))
    families = _normalize_string_list(details.get("families"))
    family = str(details.get("family", "")).lower()
    template = str(details.get("template", "")).lower()

    if "thinking" in capabilities or "reasoning" in capabilities:
        return True

    if family in OLLAMA_REASONING_FAMILIES:
        return True

    if any(item in OLLAMA_REASONING_FAMILIES for item in families):
        return True

    return any(keyword in template for keyword in OLLAMA_REASONING_KEYWORDS)


def detect_gemini_reasoning(model_metadata: Any) -> bool:
    """
    Detect Gemini reasoning support from official model metadata.

    Args:
        model_metadata: SDK model object or equivalent dict payload.

    Returns:
        True when the model exposes a thinking/reasoning capability marker.
    """
    if model_metadata is None:
        return False

    if isinstance(model_metadata, dict):
        thinking = model_metadata.get("thinking")
        supported_actions = model_metadata.get("supported_generation_methods")
    else:
        thinking = getattr(model_metadata, "thinking", None)
        supported_actions = getattr(
            model_metadata, "supported_generation_methods", None
        )

    if isinstance(thinking, bool):
        return thinking

    if isinstance(thinking, dict):
        if thinking.get("supported") is not None:
            return bool(thinking.get("supported"))
        if thinking.get("enabled") is not None:
            return bool(thinking.get("enabled"))

    if thinking is not None:
        for attr_name in ("supported", "enabled"):
            attr_value = getattr(thinking, attr_name, None)
            if attr_value is not None:
                return bool(attr_value)

    actions = _normalize_string_list(supported_actions)
    return "thinking" in actions or "reasoning" in actions


def detect_nvidia_reasoning(model_id: str) -> bool:
    """
    Detect NVIDIA reasoning support using a curated exact-id allowlist.

    Args:
        model_id: NVIDIA model identifier returned by GET /models.

    Returns:
        True when the model id is explicitly known to support reasoning.
    """
    return model_id.lower() in NVIDIA_REASONING_MODEL_IDS
