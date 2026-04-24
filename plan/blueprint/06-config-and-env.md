# 06 — Configuration & Environment

---

## Environment Variables

File: `.env.example`

```env
# ============================================
# AI Generative Core — Configuration
# ============================================

# --- App ---
APP_NAME=AI Generative Core
APP_VERSION=1.0.0
DEBUG=false

# --- Ollama (Local LLM) ---
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT=120

# --- Google Gemini ---
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_TIMEOUT=120

# --- Logging ---
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## Settings Class

File: `app/config.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # App
    APP_NAME: str = "AI Generative Core"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_TIMEOUT: int = 120

    # Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_TIMEOUT: int = 120

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" | "text"


settings = Settings()
```

---

## Validation Rules

| Variable | Required | Default | Notes |
|---|---|---|---|
| `OLLAMA_BASE_URL` | No | `localhost:11434` | Auto-detect if Ollama running |
| `GEMINI_API_KEY` | **Yes** (if using Gemini) | `""` | Empty = Gemini disabled |
| `OLLAMA_TIMEOUT` | No | `120` | Seconds |
| `GEMINI_TIMEOUT` | No | `120` | Seconds |
| `LOG_LEVEL` | No | `INFO` | DEBUG, INFO, WARNING, ERROR |

---

## Startup Validation

```python
# In main.py startup:

if settings.GEMINI_API_KEY == "":
    logger.warning("GEMINI_API_KEY not set — Gemini provider disabled")
    # Don't register Gemini provider

# Test Ollama connectivity
try:
    await httpx.AsyncClient().get(f"{settings.OLLAMA_BASE_URL}/api/tags")
except Exception:
    logger.warning("Ollama not reachable — Ollama provider disabled")
```

> **Next**: See [07-error-handling.md](./07-error-handling.md)
