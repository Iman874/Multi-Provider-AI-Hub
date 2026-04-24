# Blueprint: AI Generative Core — Caching Layer (beta0.2.4)

## 1. Visi & Tujuan

Saat ini, setiap request — meskipun prompt dan model **identik** — selalu dikirim ulang ke provider:

1. **Pemborosan Kuota**: Gemini API Key dipakai untuk prompt identik berulang
2. **Latency Tidak Perlu**: Request identik tetap menunggu 2-10 detik
3. **GPU Lokal Terbebani**: Ollama menjalankan inference ulang untuk prompt yang pernah dijawab

Modul **beta0.2.4** membangun **Response Caching Layer**:
- Cache response berdasarkan **SHA-256 hash** dari (provider + model + prompt + images)
- Cache hit → response dikembalikan **instan** tanpa memanggil provider
- Cache memiliki **TTL** (auto-expire) agar tidak stale
- **LRU eviction** saat cache penuh
- Hanya meng-cache `generate` dan `embedding` — **streaming TIDAK di-cache**
- Response bertanda `metadata.cached: true/false`
- Configurable via `.env` — bisa dimatikan sepenuhnya

---

## 2. Scope Development

### ✅ Yang Dikerjakan
- **CacheEntry Model**: Data + timestamps + hit counter
- **CacheStats Model**: Hits, misses, hit rate, evictions
- **CacheService**: In-memory OrderedDict, TTL, LRU eviction, thread-safe
- **Cache Key Generation**: SHA-256 deterministic hash
- **GeneratorService Integration**: Check cache before provider call
- **Cache Stats Endpoint**: `GET /api/v1/cache/stats`
- **Cache Clear Endpoint**: `DELETE /api/v1/cache`
- **Unit Tests**

### ❌ Yang Tidak Dikerjakan
- Redis/external cache (in-memory only)
- Streaming response caching (only generate + embedding)
- Semantic similarity caching (exact match only)
- Per-user cache isolation
- Disk persistence (restart = cache cleared)

---

## 3. Arsitektur & Desain

### 3.1. Konfigurasi (`.env`)

```env
# --- Caching ---
CACHE_ENABLED=true       # true/false — master switch
CACHE_TTL=300            # TTL in seconds (5 minutes)
CACHE_MAX_SIZE=1000      # Max entries (LRU eviction when full)
```

**Config di `app/config.py`**:
```python
CACHE_ENABLED: bool = True
CACHE_TTL: int = 300
CACHE_MAX_SIZE: int = 1000
```

### 3.2. Data Models

```python
@dataclass
class CacheEntry:
    key: str                # SHA-256 hash
    response: dict          # Cached response dict
    created_at: float       # time.time() saat disimpan
    last_accessed: float    # Updated setiap cache hit (untuk LRU)
    hit_count: int = 0      # Berapa kali di-access

@dataclass
class CacheStats:
    total_hits: int         # Total cache hits
    total_misses: int       # Total cache misses
    hit_rate: float         # hits / (hits + misses), 0.0 jika belum ada request
    current_size: int       # Entries in cache saat ini
    max_size: int           # Max capacity
    evictions: int          # Total LRU evictions
```

### 3.3. Cache Key Strategy

Cache key menggunakan **SHA-256 hash** dari komponen request yang di-normalize:

```python
import hashlib

def make_key(provider: str, model: str, prompt: str, images: list[str] | None = None) -> str:
    """
    Generate deterministic cache key.

    Normalization:
    - prompt di-strip whitespace
    - images: hash setiap base64 string, sort, join
    - Semua komponen di-join dengan "|" separator
    """
    parts = [provider, model, prompt.strip()]

    if images:
        # Hash setiap image dan sort untuk deterministic order
        img_hashes = sorted(hashlib.md5(img.encode()).hexdigest() for img in images)
        parts.append(",".join(img_hashes))
    else:
        parts.append("")

    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()
```

**Contoh:**
```
Input:  provider="gemini", model="gemini-2.5-pro", prompt="Apa itu AI?"
Key:    sha256("gemini|gemini-2.5-pro|Apa itu AI?|")
Result: "a3f2b7c8d1e5..."  (64 char hex)

Input:  prompt="Apa itu AI?" (sama) → key SAMA → cache HIT
Input:  prompt="Apa itu ML?" (beda) → key BEDA → cache MISS
```

### 3.4. CacheService (`app/services/cache_service.py`)

```
┌─────────────────────────────────────────────────────────┐
│                  CacheService                           │
├─────────────────────────────────────────────────────────┤
│ _cache: OrderedDict[str, CacheEntry]                    │
│ _max_size: int                                          │
│ _ttl: int                                               │
│ _enabled: bool                                          │
│ _lock: threading.Lock                                   │
│ _hits: int                                              │
│ _misses: int                                            │
│ _evictions: int                                         │
├─────────────────────────────────────────────────────────┤
│ make_key(provider, model, prompt, images?) → str        │
│ get(key) → dict | None                                  │
│ put(key, response)                                      │
│ invalidate(key) → bool                                  │
│ clear() → int  (returns count cleared)                  │
│ get_stats() → CacheStats                                │
│ is_enabled → bool                                       │
└─────────────────────────────────────────────────────────┘
```

**Pseudocode `get(key)`**:
```python
def get(self, key: str) -> dict | None:
    if not self._enabled:
        return None

    with self._lock:
        entry = self._cache.get(key)

        if entry is None:
            self._misses += 1
            return None

        # TTL check
        if time.time() - entry.created_at > self._ttl:
            # Expired — remove and count as miss
            del self._cache[key]
            self._misses += 1
            return None

        # Cache HIT
        entry.last_accessed = time.time()
        entry.hit_count += 1
        self._hits += 1

        # Move to end for LRU ordering
        self._cache.move_to_end(key)

        return entry.response
```

**Pseudocode `put(key, response)`**:
```python
def put(self, key: str, response: dict) -> None:
    if not self._enabled:
        return

    with self._lock:
        # Jika key sudah ada, update
        if key in self._cache:
            self._cache[key].response = response
            self._cache[key].created_at = time.time()
            self._cache[key].last_accessed = time.time()
            self._cache.move_to_end(key)
            return

        # Evict LRU jika penuh
        while len(self._cache) >= self._max_size:
            oldest_key, _ = self._cache.popitem(last=False)  # Remove first (LRU)
            self._evictions += 1
            logger.debug("Cache evicted: {key}", key=oldest_key[:8])

        # Insert new entry
        self._cache[key] = CacheEntry(
            key=key,
            response=response,
            created_at=time.time(),
            last_accessed=time.time(),
        )
```

**Pseudocode `get_stats()`**:
```python
def get_stats(self) -> CacheStats:
    total = self._hits + self._misses
    return CacheStats(
        total_hits=self._hits,
        total_misses=self._misses,
        hit_rate=self._hits / total if total > 0 else 0.0,
        current_size=len(self._cache),
        max_size=self._max_size,
        evictions=self._evictions,
    )
```

### 3.5. GeneratorService Integration

**File**: `app/services/generator.py`

Update `generate()` method:
```python
async def generate(self, request: GenerateRequest) -> dict:
    # ... existing validation ...

    # 1. Check cache (BEFORE calling provider)
    cache_key = None
    if self._cache and self._cache.is_enabled:
        cache_key = self._cache.make_key(
            provider=request.provider,
            model=request.model,
            prompt=request.input,
            images=request.images,
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("Cache HIT for key {k}", k=cache_key[:8])
            # Add cache metadata
            cached["metadata"] = {
                "cached": True,
                "cache_age_seconds": int(time.time() - ...),
            }
            return cached

    # 2. Call provider (cache MISS)
    result = await provider.generate(model=..., prompt=..., images=...)

    # 3. Store in cache
    if cache_key and self._cache:
        self._cache.put(cache_key, result)

    # 4. Add metadata
    result["metadata"] = {"cached": False}
    return result
```

**Yang TIDAK di-cache:**
- `stream()` — streaming responses
- Responses with errors

**Yang DI-cache:**
- `generate()` — text/multimodal generation
- `embedding()` — vector embeddings (identical input → identical output)

### 3.6. Cache Endpoints

**`GET /api/v1/cache/stats`**:
```json
{
  "total_hits": 42,
  "total_misses": 158,
  "hit_rate": 0.21,
  "current_size": 87,
  "max_size": 1000,
  "evictions": 3
}
```

**`DELETE /api/v1/cache`**:
```json
{
  "message": "Cache cleared",
  "entries_removed": 87
}
```

### 3.7. Response Metadata

Response yang melewati cache layer ditandai:

```json
{
  "output": "Machine learning adalah...",
  "provider": "gemini",
  "model": "gemini-2.5-pro",
  "usage": { ... },
  "metadata": {
    "cached": true,
    "cache_age_seconds": 42
  }
}
```

- `cached: true` → response dari cache, `cache_age_seconds` menunjukkan umur
- `cached: false` → response fresh dari provider

---

## 4. Breakdowns (Daftar Task)

### Task 1 — Config & Data Models
**Files**: `app/config.py`, `app/services/cache_service.py` (partial)
- Config: `CACHE_ENABLED`, `CACHE_TTL`, `CACHE_MAX_SIZE`
- Dataclass: `CacheEntry`, `CacheStats`
- **Estimasi:** 15 menit

### Task 2 — CacheService Core
**Files**: `app/services/cache_service.py`
- Class `CacheService` with `OrderedDict`, `Lock`, `make_key`, `get` (TTL+LRU), `put` (eviction), `invalidate`, `clear`, `get_stats`
- SHA-256 key generation with normalization
- Thread-safe operations
- **Estimasi:** 45 menit

### Task 3 — GeneratorService Integration
**Files**: `app/services/generator.py`, `app/api/dependencies.py`
- Init `CacheService` in `initialize_services()`
- Inject into `GeneratorService.__init__()`
- Update `generate()`: cache check → provider call → cache store
- Update `embedding()`: same pattern
- `stream()`: NO caching
- Add `metadata.cached` to responses
- **Estimasi:** 30 menit

### Task 4 — Cache Endpoints
**Files**: `app/api/endpoints/cache.py`, `app/api/router.py`, `app/schemas/responses.py`
- `GET /api/v1/cache/stats` → CacheStats response
- `DELETE /api/v1/cache` → flush + count
- Register router, response schemas
- **Estimasi:** 20 menit

### Task 5 — Unit Tests
**Files**: `tests/services/test_cache_service.py` (12 tests)
1. `test_cache_hit` — put then get → response returned
2. `test_cache_miss` — get without put → None
3. `test_ttl_expiry` — expired entry → None (mock time)
4. `test_lru_eviction` — full cache → oldest removed
5. `test_make_key_deterministic` — same input → same key
6. `test_make_key_different_prompt` — different prompt → different key
7. `test_make_key_different_model` — different model → different key
8. `test_invalidate` — single entry removed
9. `test_clear` — all entries removed, returns count
10. `test_stats_accuracy` — hits/misses/hit_rate correct
11. `test_disabled_cache` — enabled=False → always None
12. `test_put_updates_existing` — same key → response updated
- **Estimasi:** 45 menit

---

## 5. Timeline & Estimasi Total

| Task | Scope | Estimasi |
|---|---|---|
| Task 1 | Config & Data Models | 15 menit |
| Task 2 | CacheService Core | 45 menit |
| Task 3 | GeneratorService Integration | 30 menit |
| Task 4 | Cache Endpoints | 20 menit |
| Task 5 | Unit Tests | 45 menit |
| **Total** | | **~2.6 jam** |

---

## 6. Acceptance Criteria Global

- [ ] Response caching berfungsi untuk `generate` dan `embedding`
- [ ] Streaming **TIDAK** di-cache
- [ ] Cache key deterministic: SHA-256(provider + model + prompt + images)
- [ ] TTL berfungsi — expired entries treated as miss
- [ ] LRU eviction saat `current_size >= max_size`
- [ ] Response cached ditandai `metadata.cached: true` + `cache_age_seconds`
- [ ] Response fresh ditandai `metadata.cached: false`
- [ ] `GET /cache/stats` — hit rate, size, evictions
- [ ] `DELETE /cache` — flush semua entries
- [ ] `CACHE_ENABLED=false` → bypass semua logic (zero overhead)
- [ ] Thread-safe untuk concurrent requests
- [ ] Semua existing tests tetap PASS
- [ ] 12 test baru ditambahkan
