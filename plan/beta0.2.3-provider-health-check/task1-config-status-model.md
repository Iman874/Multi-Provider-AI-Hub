# Task 1 — Config & ProviderStatus Data Model

## 1. Judul Task
Tambah konfigurasi Health Check dan dataclass `ProviderStatus` sebagai foundation

## 2. Deskripsi
Menyiapkan foundation layer untuk fitur Provider Health Check: 3 config fields baru di Settings, dataclass `ProviderStatus` untuk menyimpan status setiap provider, dan update `.env`.

## 3. Tujuan Teknis
- `settings.HEALTH_CHECK_INTERVAL`, `settings.HEALTH_CHECK_TIMEOUT`, `settings.HEALTH_CHECK_THRESHOLD` bisa diakses
- `ProviderStatus` dataclass tersedia dengan semua field yang dibutuhkan
- `APP_VERSION` terupdate ke `"0.2.3"`
- `.env` dan `.env.example` terupdate

## 4. Scope
### Yang dikerjakan
- `app/config.py` — tambah 3 field config, update version
- `app/services/health_checker.py` — file baru (partial: hanya dataclass + imports)
- `.env` — tambah 3 variabel baru
- `.env.example` — update

### Yang TIDAK dikerjakan
- HealthChecker service logic — Task 2
- Endpoint / Router — Task 3
- Background monitor — Task 4
- Unit tests — Task 5

## 5. Langkah Implementasi

### Step 1: Update `app/config.py`
Tambahkan 3 field baru di class `Settings`, setelah section `# --- Logging ---`:
```python
# --- Health Check ---
HEALTH_CHECK_INTERVAL: int = 30    # Seconds between periodic health checks
HEALTH_CHECK_TIMEOUT: int = 5      # Probe timeout in seconds
HEALTH_CHECK_THRESHOLD: int = 3    # Consecutive failures before marking DOWN
```
Ubah `APP_VERSION` dari current value menjadi `"0.2.3"`.

### Step 2: Buat file `app/services/health_checker.py` (partial — dataclass only)
Buat file baru dengan imports dan `ProviderStatus` dataclass:

```python
"""
Health Checker — Provider health monitoring service.

Probes AI providers periodically to determine availability.
Tracks status (up/down/degraded), latency, and failure streaks.
Used by model listing to filter unavailable providers and by
the health endpoint to report system status.
"""

import time
from dataclasses import dataclass

from loguru import logger


@dataclass
class ProviderStatus:
    """Current health status of an AI provider."""

    provider: str                       # "ollama" | "gemini"
    status: str = "up"                  # "up" | "down" | "degraded"
    last_check: float = 0.0            # Unix timestamp of last probe
    last_success: float | None = None   # Last successful probe timestamp
    consecutive_failures: int = 0       # Failure streak count
    latency_ms: float | None = None     # Last probe latency in milliseconds
    error_message: str | None = None    # Last error detail (if any)
```

### Step 3: Update `.env`
Tambahkan di akhir file:
```env
# --- Health Check ---
# Seconds between periodic health checks
HEALTH_CHECK_INTERVAL=30
# Probe timeout in seconds
HEALTH_CHECK_TIMEOUT=5
# Consecutive failures before marking provider as DOWN
HEALTH_CHECK_THRESHOLD=3
```

### Step 4: Update `.env.example`
Sama seperti `.env`:
```env
# --- Health Check ---
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=5
HEALTH_CHECK_THRESHOLD=3
```

## 6. Output yang Diharapkan

Setelah task selesai, verifikasi dengan script:
```python
from app.config import settings
from app.services.health_checker import ProviderStatus

# Config
assert settings.APP_VERSION == "0.2.3"
assert settings.HEALTH_CHECK_INTERVAL == 30
assert settings.HEALTH_CHECK_TIMEOUT == 5
assert settings.HEALTH_CHECK_THRESHOLD == 3

# ProviderStatus
status = ProviderStatus(provider="ollama")
assert status.provider == "ollama"
assert status.status == "up"
assert status.consecutive_failures == 0
assert status.latency_ms is None
assert status.error_message is None

# With values
status2 = ProviderStatus(
    provider="gemini",
    status="down",
    last_check=1700000000.0,
    consecutive_failures=5,
    error_message="Connection refused",
)
assert status2.status == "down"
assert status2.consecutive_failures == 5

print("All checks passed!")
```

## 7. Dependencies
- Tidak ada (task pertama, foundation layer)

## 8. Acceptance Criteria
- [ ] `settings.HEALTH_CHECK_INTERVAL` accessible, default `30`
- [ ] `settings.HEALTH_CHECK_TIMEOUT` accessible, default `5`
- [ ] `settings.HEALTH_CHECK_THRESHOLD` accessible, default `3`
- [ ] `APP_VERSION` = `"0.2.3"`
- [ ] `ProviderStatus` dataclass: provider, status (default "up"), last_check, last_success, consecutive_failures (default 0), latency_ms, error_message
- [ ] `.env` punya 3 variabel health check baru
- [ ] Server bisa start tanpa error: `uvicorn app.main:app --reload --port 8000`
- [ ] Semua existing tests tetap PASS

## 9. Estimasi
Low (~15 menit)
