# Task 4 — Logging System

> **Modul**: beta0.1.1 — Foundation Core  
> **Estimasi**: Low (30–45 menit)  
> **Dependencies**: Task 2 (Configuration System)

---

## 1. Judul Task

Implementasi `app/core/logging.py` — Loguru-based logging setup dengan format JSON dan text yang configurable.

---

## 2. Deskripsi

Membuat sistem logging terpusat menggunakan loguru. Logging di-setup sekali saat startup dan digunakan di seluruh aplikasi. Format output (JSON atau text) dan level bisa dikonfigurasi via environment variables.

---

## 3. Tujuan Teknis

- Fungsi `setup_logging()` yang mengkonfigurasi loguru
- Support 2 format output: JSON (untuk production) dan text (untuk development)
- Level dikonfigurasi dari `settings.LOG_LEVEL`
- Remove default loguru handler, replace dengan custom handler
- Return logger instance yang siap dipakai

---

## 4. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/core/logging.py`
- Fungsi `setup_logging(log_level, log_format)`
- Console output dengan format yang configurable

### ❌ Yang Tidak Dikerjakan

- File output (log ke file) — bisa ditambah nanti
- Log rotation — not needed untuk versi ini
- Request/response logging — itu di task 5 (middleware)

---

## 5. Langkah Implementasi

### Step 1: Buat `app/core/logging.py`

```python
"""
Logging configuration for AI Generative Core.

Uses loguru for structured logging with support for JSON and text formats.
Call setup_logging() once during application startup.
"""

import sys

from loguru import logger


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """
    Configure application-wide logging.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format: Output format - "json" for structured or "text" for human-readable.
    """
    # Remove default loguru handler
    logger.remove()

    if log_format == "json":
        # JSON format for production / log aggregation
        logger.add(
            sys.stdout,
            level=log_level.upper(),
            format="{message}",
            serialize=True,
        )
    else:
        # Human-readable text format for development
        logger.add(
            sys.stdout,
            level=log_level.upper(),
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            colorize=True,
        )

    logger.info(
        "Logging initialized",
        level=log_level,
        format=log_format,
    )
```

### Step 2: Verifikasi

```bash
python -c "
from app.core.logging import setup_logging
from loguru import logger

# Test text format
setup_logging(log_level='DEBUG', log_format='text')
logger.debug('This is a debug message')
logger.info('This is an info message')
logger.warning('This is a warning')
logger.error('This is an error')
"
```

Output yang diharapkan (text format):

```
2026-04-22 22:00:00 | INFO     | app.core.logging:setup_logging:42 | Logging initialized
2026-04-22 22:00:00 | DEBUG    | __main__:<module>:7 | This is a debug message
2026-04-22 22:00:00 | INFO     | __main__:<module>:8 | This is an info message
2026-04-22 22:00:00 | WARNING  | __main__:<module>:9 | This is a warning
2026-04-22 22:00:00 | ERROR    | __main__:<module>:10 | This is an error
```

Test JSON format:

```bash
python -c "
from app.core.logging import setup_logging
from loguru import logger
setup_logging(log_level='INFO', log_format='json')
logger.info('Server starting')
"
```

Output: satu baris JSON per log entry.

---

## 6. Output yang Diharapkan

### File: `app/core/logging.py`

Isi seperti Step 1 di atas.

### Behavior

| `LOG_FORMAT` | Output |
|---|---|
| `"text"` | Colored, human-readable: `2026-04-22 ... \| INFO \| message` |
| `"json"` | Serialized JSON: `{"text": "...", "level": "INFO", ...}` |

| `LOG_LEVEL` | Yang terlihat |
|---|---|
| `"DEBUG"` | Semua log |
| `"INFO"` | INFO, WARNING, ERROR, CRITICAL |
| `"WARNING"` | WARNING, ERROR, CRITICAL |
| `"ERROR"` | ERROR, CRITICAL |

---

## 7. Dependencies

- **Task 2** — `settings.LOG_LEVEL` dan `settings.LOG_FORMAT` harus tersedia
- **Package**: `loguru` harus terinstall

---

## 8. Acceptance Criteria

- [ ] File `app/core/logging.py` ada
- [ ] `setup_logging("DEBUG", "text")` → colored console output
- [ ] `setup_logging("INFO", "json")` → JSON output ke stdout
- [ ] Log level `DEBUG` menampilkan semua message
- [ ] Log level `WARNING` menyembunyikan DEBUG dan INFO
- [ ] Default handler loguru di-remove (tidak ada duplikat log)
- [ ] `from loguru import logger` bisa digunakan di file manapun setelah setup

---

## 9. Estimasi

**Low** — Loguru API sangat straightforward.
