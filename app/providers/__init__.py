"""
Provider factory for AI Generative Core.

Provides a single function to create provider instances by name.
This is the only place where provider classes are imported and instantiated.
"""

from loguru import logger

from app.config import Settings
from app.providers.base import BaseProvider
from app.providers.ollama import OllamaProvider
from app.providers.gemini import GeminiProvider
from app.providers.nvidia import NvidiaProvider
from app.services.key_manager import KeyManager

def _parse_keys(csv_string: str) -> list[str]:
    """
    Parse comma-separated API keys string into a list.

    Strips whitespace, filters empty strings.
    "key1,key2,key3" → ["key1", "key2", "key3"]
    "" → []
    """
    if not csv_string or not csv_string.strip():
        return []
    return [k.strip() for k in csv_string.split(",") if k.strip()]

def create_provider(provider_name: str, settings: Settings) -> BaseProvider | None:
    """
    Factory function to create a provider instance by name.
    """
    match provider_name:
        case "ollama":
            # Parse Ollama Cloud API keys (opsional)
            ollama_keys = _parse_keys(settings.OLLAMA_API_KEYS)
            key_manager = None
            if ollama_keys:
                key_manager = KeyManager(
                    name="ollama_cloud",
                    keys=ollama_keys,
                )
                logger.info(
                    "Ollama Cloud: {count} API key(s) loaded",
                    count=len(ollama_keys),
                )

            return OllamaProvider(
                base_url=settings.OLLAMA_BASE_URL,
                timeout=settings.OLLAMA_TIMEOUT,
                key_manager=key_manager,
            )

        case "gemini":
            # Parse Gemini API keys (multi → fallback single)
            gemini_keys = _parse_keys(settings.GEMINI_API_KEYS)
            if not gemini_keys:
                # Fallback ke single key lama
                if settings.GEMINI_API_KEY:
                    gemini_keys = [settings.GEMINI_API_KEY]
                else:
                    logger.warning(
                        "Gemini provider skipped: no API keys configured"
                    )
                    return None

            key_manager = KeyManager(
                name="gemini",
                keys=gemini_keys,
            )
            logger.info(
                "Gemini: {count} API key(s) loaded",
                count=len(gemini_keys),
            )

            return GeminiProvider(
                key_manager=key_manager,
                timeout=settings.GEMINI_TIMEOUT,
            )

        case "nvidia":
            # NVIDIA NIM — single API key (nvapi-...)
            if not settings.NVIDIA_API_KEY:
                logger.warning(
                    "NVIDIA NIM provider skipped: no API key configured"
                )
                return None

            logger.info("NVIDIA NIM: API key loaded")

            return NvidiaProvider(
                api_key=settings.NVIDIA_API_KEY,
                base_url=settings.NVIDIA_BASE_URL,
                timeout=settings.NVIDIA_TIMEOUT,
            )

        case _:
            raise ValueError(f"Unknown provider: '{provider_name}'")
