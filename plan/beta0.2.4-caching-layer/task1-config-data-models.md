# Task 1 — Config & Data Models

## 1. Judul Task
Tambah konfigurasi Caching Layer dan dataclasses `CacheEntry`/`CacheStats` sebagai foundation

## 2. Deskripsi
Menyiapkan foundation layer untuk fitur Response Caching: 3 config fields baru di Settings (enabled switch, TTL, max size), dan 2 dataclasses untuk menyimpan cache entries dan statistik.

## 3. Tujuan Teknis
- `settings.CACHE_ENABLED`, `settings.CACHE_TTL`, `settings.CACHE_MAX_SIZE` bisa diakses
- `CacheEntry` dataclass tersedia dengan semua field (key, response, timestamps, hit_count)
- `CacheStats` dataclass tersedia (hits, misses, hit_rate, size, max_size, evictions)
- `APP_VERSION` terupdate ke `"0.2.4"`
- `.env` dan `.env.example` terupdate

## 4. Scope
### Yang dikerjakan
- `app/config.py` — tambah 3 field config, update version
- `app/services/cache_service.py` — file baru (partial: hanya dataclasses + imports)
- `.env` — tambah 3 variabel baru
- `.env.example` — update

### Yang TIDAK dikerjakan
- CacheService logic (get, put, eviction) — Task 2
- GeneratorService integration — Task 3
- Endpoints — Task 4
- Unit tests — Task 5

## 5. Langkah Implementasi

### Step 1: Update `app/config.py`
Tambahkan 3 field baru di class `Settings`, setelah section `# --- Logging ---`:
```python
# --- Caching ---
CACHE_ENABLED: bool = True       # Master switch — false = bypass all cache logic
CACHE_TTL: int = 300             # Cache TTL in seconds (5 minutes)
CACHE_MAX_SIZE: int = 1000       # Max cache entries (LRU eviction when full)
```
Ubah `APP_VERSION` dari current value menjadi `"0.2.4"`.

### Step 2: Buat file `app/services/cache_service.py` (partial — dataclasses only)
Buat file baru:

```python
"""
Cache Service — In-memory response caching with TTL and LRU eviction.

Caches AI provider responses (generate + embedding) to reduce latency
and API quota usage. Uses SHA-256 hash keys for deterministic cache
lookups. Thread-safe via threading.Lock.
"""

import time
from dataclasses import dataclass

from loguru import logger


@dataclass
class CacheEntry:
    """A cached response entry with metadata."""

    key: str                # SHA-256 hash of request components
    response: dict          # Cached response dictionary
    created_at: float       # time.time() when stored
    last_accessed: float    # Updated on every cache hit (for LRU)
    hit_count: int = 0      # How many times this entry was accessed


@dataclass
class CacheStats:
    """Aggregate cache statistics."""

    total_hits: int         # Total cache hits
    total_misses: int       # Total cache misses
    hit_rate: float         # hits / (hits + misses), 0.0 if no requests
    current_size: int       # Current number of entries in cache
    max_size: int           # Maximum cache capacity
    evictions: int          # Total LRU evictions performed
```

### Step 3: Update `.env`
Tambahkan di akhir file:
```env
# --- Caching ---
# Master switch for response caching (true/false)
CACHE_ENABLED=true
# Cache TTL in seconds (entries expire after this)
CACHE_TTL=300
# Max cache entries (LRU eviction when full)
CACHE_MAX_SIZE=1000
```

### Step 4: Update `.env.example`
Sama seperti `.env`:
```env
# --- Caching ---
CACHE_ENABLED=true
CACHE_TTL=300
CACHE_MAX_SIZE=1000
```

## 6. Output yang Diharapkan

Setelah task selesai, verifikasi:
```python
from app.config import settings
from app.services.cache_service import CacheEntry, CacheStats

# Config
assert settings.APP_VERSION == "0.2.4"
assert settings.CACHE_ENABLED is True
assert settings.CACHE_TTL == 300
assert settings.CACHE_MAX_SIZE == 1000

# CacheEntry
entry = CacheEntry(
    key="abc123",
    response={"output": "Hello"},
    created_at=1700000000.0,
    last_accessed=1700000000.0,
)
assert entry.hit_count == 0
assert entry.key == "abc123"

# CacheStats
stats = CacheStats(
    total_hits=42,
    total_misses=158,
    hit_rate=0.21,
    current_size=87,
    max_size=1000,
    evictions=3,
)
assert stats.hit_rate == 0.21

print("All checks passed!")
```

## 7. Dependencies
- Tidak ada (task pertama, foundation layer)

## 8. Acceptance Criteria
- [ ] `settings.CACHE_ENABLED` accessible, default `True`
- [ ] `settings.CACHE_TTL` accessible, default `300`
- [ ] `settings.CACHE_MAX_SIZE` accessible, default `1000`
- [ ] `APP_VERSION` = `"0.2.4"`
- [ ] `CacheEntry` dataclass: key, response, created_at, last_accessed, hit_count (default 0)
- [ ] `CacheStats` dataclass: total_hits, total_misses, hit_rate, current_size, max_size, evictions
- [ ] `.env` punya 3 variabel caching baru
- [ ] Server bisa start tanpa error: `uvicorn app.main:app --reload --port 8000`
- [ ] Semua existing tests tetap PASS

## 9. Estimasi
Low (~15 menit)
