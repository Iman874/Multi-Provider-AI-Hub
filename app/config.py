"""
Application configuration.

Loads settings from environment variables and .env file.
Used by all layers (providers, services, API) to access configuration.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized application settings.
    
    Values are loaded from:
    1. Environment variables (highest priority)
    2. .env file (fallback)
    3. Default values defined here (lowest priority)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # --- App ---
    APP_NAME: str = "AI Generative Core"
    APP_VERSION: str = "0.2.8"
    DEBUG: bool = False

    # --- Ollama (Local LLM) ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_TIMEOUT: int = 120
    OLLAMA_API_KEYS: str = ""

    # --- Google Gemini ---
    GEMINI_API_KEY: str = ""
    GEMINI_API_KEYS: str = ""
    GEMINI_TIMEOUT: int = 120

    # --- NVIDIA NIM ---
    NVIDIA_API_KEY: str = ""          # nvapi-... key from build.nvidia.com
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_TIMEOUT: int = 120

    # --- Logging ---
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" | "text"

    # --- Caching ---
    CACHE_ENABLED: bool = True       # Master switch — false = bypass all cache logic
    CACHE_TTL: int = 300             # Cache TTL in seconds (5 minutes)
    CACHE_MAX_SIZE: int = 1000       # Max cache entries (LRU eviction when full)

    # --- Conversation History ---
    CHAT_MAX_HISTORY: int = 50    # Max messages per session (trim FIFO, system prompt preserved)
    CHAT_SESSION_TTL: int = 30    # Session TTL in minutes (auto-expire inactive sessions)

    # --- Health Check ---
    HEALTH_CHECK_INTERVAL: int = 30    # Seconds between periodic health checks
    HEALTH_CHECK_TIMEOUT: int = 5      # Probe timeout in seconds
    HEALTH_CHECK_THRESHOLD: int = 3    # Consecutive failures before marking DOWN

    # --- Batch Processing ---
    BATCH_MAX_SIZE: int = 20      # Maximum items per batch request
    BATCH_CONCURRENCY: int = 5    # Max concurrent provider calls within a batch

    # --- Gateway Auth ---
    GATEWAY_TOKEN: str = ""       # Static service token, kosong = auth disabled
    RATE_LIMIT_RPM: int = 120     # Max requests per minute, 0 = unlimited


# Singleton instance — import this everywhere
settings = Settings()
