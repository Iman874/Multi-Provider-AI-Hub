# Task 2 — Configuration System

> **Modul**: beta0.1.1 — Foundation Core  
> **Estimasi**: Low (30–60 menit)  
> **Dependencies**: Task 1 (Project Scaffolding)

---

## 1. Judul Task

Implementasi `app/config.py` — Settings class dengan pydantic-settings untuk load environment variables.

---

## 2. Deskripsi

Membuat sistem konfigurasi terpusat yang membaca environment variables dari file `.env` dan menyediakan typed settings object yang bisa diimport dari mana saja di project.

---

## 3. Tujuan Teknis

- Class `Settings` yang extend `BaseSettings` dari pydantic-settings
- Semua variabel environment terdefinisi dengan type hint dan default value
- Auto-load dari file `.env`
- Singleton instance `settings` siap diimport
- Copy `.env.example` → `.env` sebagai working config

---

## 4. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/config.py`
- Copy `.env.example` → `.env` untuk local development

### ❌ Yang Tidak Dikerjakan

- Validasi koneksi provider (Ollama/Gemini) — itu di task 6
- Dynamic config reload
- Config profiles (dev/staging/prod)

---

## 5. Langkah Implementasi

### Step 1: Buat `app/config.py`

```python
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
    APP_VERSION: str = "0.1.1"
    DEBUG: bool = False

    # --- Ollama (Local LLM) ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_TIMEOUT: int = 120

    # --- Google Gemini ---
    GEMINI_API_KEY: str = ""
    GEMINI_TIMEOUT: int = 120

    # --- Logging ---
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" | "text"


# Singleton instance — import this everywhere
settings = Settings()
```

### Step 2: Copy `.env.example` → `.env`

Salin file `.env.example` menjadi `.env` dan isi dengan nilai yang sesuai untuk local development:

```env
APP_NAME=AI Generative Core
APP_VERSION=0.1.1
DEBUG=true

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT=120

GEMINI_API_KEY=
GEMINI_TIMEOUT=120

LOG_LEVEL=DEBUG
LOG_FORMAT=text
```

Note: `GEMINI_API_KEY` boleh kosong — provider Gemini akan disabled.

### Step 3: Verifikasi

Jalankan dari root project:

```bash
python -c "from app.config import settings; print(settings.APP_NAME); print(settings.OLLAMA_BASE_URL)"
```

Harus output:

```
AI Generative Core
http://localhost:11434
```

---

## 6. Output yang Diharapkan

### File: `app/config.py`

Isi seperti Step 1 di atas.

### Behavior

```python
from app.config import settings

settings.APP_NAME          # "AI Generative Core"
settings.APP_VERSION       # "0.1.1"
settings.DEBUG             # True (dari .env DEBUG=true)
settings.OLLAMA_BASE_URL   # "http://localhost:11434"
settings.OLLAMA_TIMEOUT    # 120
settings.GEMINI_API_KEY    # "" (kosong)
settings.GEMINI_TIMEOUT    # 120
settings.LOG_LEVEL         # "DEBUG" (dari .env)
settings.LOG_FORMAT        # "text" (dari .env)
```

---

## 7. Dependencies

- **Task 1** — folder `app/` dan `__init__.py` harus ada
- **Package**: `pydantic-settings` harus terinstall

---

## 8. Acceptance Criteria

- [ ] File `app/config.py` ada dan bisa di-import tanpa error
- [ ] `from app.config import settings` berhasil
- [ ] `settings.APP_NAME` return `"AI Generative Core"`
- [ ] `settings.OLLAMA_BASE_URL` return `"http://localhost:11434"`
- [ ] Jika `.env` berisi `DEBUG=true`, maka `settings.DEBUG` = `True`
- [ ] Jika variabel tidak ada di `.env`, default value digunakan
- [ ] File `.env` ada (copy dari `.env.example`)
- [ ] `.env` tercantum di `.gitignore`

---

## 9. Estimasi

**Low** — Straightforward pydantic-settings implementation.
