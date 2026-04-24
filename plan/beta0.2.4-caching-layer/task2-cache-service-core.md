# Task 2 — CacheService Core (OrderedDict + LRU + TTL)

## 1. Judul Task
Implementasi `CacheService` dengan SHA-256 key generation, OrderedDict LRU eviction, TTL expiry, dan thread-safe operations

## 2. Deskripsi
Membangun service caching inti yang menyimpan response dalam `OrderedDict` untuk mendukung LRU ordering. Service menggunakan `threading.Lock` untuk thread-safety, SHA-256 hash untuk cache key deterministic, dan TTL-based expiry.

## 3. Tujuan Teknis
- `CacheService` menyediakan: `make_key()`, `get()`, `put()`, `invalidate()`, `clear()`, `get_stats()`, `is_enabled`
- `make_key()` — SHA-256 hash dari (provider + model + prompt + images), deterministic
- `get()` — TTL check, LRU reorder, hit/miss tracking
- `put()` — LRU eviction saat penuh, update existing entries
- Thread-safe via `threading.Lock`
- Disabled mode: `CACHE_ENABLED=false` → semua operasi no-op

## 4. Scope
### Yang dikerjakan
- `app/services/cache_service.py` — extend file dari Task 1, tambah `CacheService` class

### Yang TIDAK dikerjakan
- GeneratorService integration — Task 3
- Endpoints — Task 4
- Dependency injection — Task 3
- Unit tests — Task 5

## 5. Langkah Implementasi

### Step 1: Tambah imports di `app/services/cache_service.py`
Update imports (extend dari Task 1):
```python
import hashlib
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass

from loguru import logger
```

### Step 2: Implementasi `CacheService.__init__()`
Tambahkan class setelah dataclasses:

```python
class CacheService:
    """
    In-memory response cache with TTL and LRU eviction.

    Uses OrderedDict for O(1) LRU operations and threading.Lock
    for thread-safety under concurrent requests.
    """

    def __init__(
        self,
        enabled: bool = True,
        ttl: int = 300,
        max_size: int = 1000,
    ):
        """
        Initialize CacheService.

        Args:
            enabled: Master switch. If False, all operations are no-op.
            ttl: Time-to-live in seconds for cache entries.
            max_size: Maximum number of entries before LRU eviction.
        """
        self._enabled = enabled
        self._ttl = ttl
        self._max_size = max_size
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        logger.info(
            "CacheService initialized: enabled={enabled}, ttl={ttl}s, max_size={max_size}",
            enabled=enabled,
            ttl=ttl,
            max_size=max_size,
        )
```

### Step 3: Implementasi `make_key()` — SHA-256 deterministic hash
```python
    @staticmethod
    def make_key(
        provider: str,
        model: str,
        prompt: str,
        images: list[str] | None = None,
    ) -> str:
        """
        Generate a deterministic SHA-256 cache key from request components.

        Normalization:
        - prompt whitespace is stripped
        - images: each base64 string is MD5-hashed, sorted, joined
        - All components joined with "|" separator

        Args:
            provider: Provider name (e.g. "ollama").
            model: Model name (e.g. "llama3.2").
            prompt: User prompt text.
            images: Optional list of base64-encoded image strings.

        Returns:
            64-character hex SHA-256 hash string.
        """
        parts = [provider, model, prompt.strip()]

        if images:
            # Hash each image and sort for deterministic order
            img_hashes = sorted(
                hashlib.md5(img.encode()).hexdigest() for img in images
            )
            parts.append(",".join(img_hashes))
        else:
            parts.append("")

        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()
```

### Step 4: Implementasi `get()` — TTL check + LRU reorder + hit/miss tracking
```python
    def get(self, key: str) -> dict | None:
        """
        Retrieve a cached response by key.

        Returns None if:
        - Cache is disabled
        - Key not found (miss)
        - Entry expired (TTL exceeded — entry removed)

        On hit:
        - Updates last_accessed timestamp
        - Increments hit_count
        - Moves entry to end of OrderedDict (most recently used)

        Args:
            key: SHA-256 cache key.

        Returns:
            Cached response dict, or None on miss/expired.
        """
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

            # Move to end for LRU ordering (most recently used)
            self._cache.move_to_end(key)

            return entry.response
```

### Step 5: Implementasi `put()` — LRU eviction saat penuh
```python
    def put(self, key: str, response: dict) -> None:
        """
        Store a response in the cache.

        If the key already exists, updates the response and timestamps.
        If the cache is full, evicts the least recently used (LRU) entry.

        No-op if cache is disabled.

        Args:
            key: SHA-256 cache key.
            response: Response dict to cache.
        """
        if not self._enabled:
            return

        with self._lock:
            # Update existing entry
            if key in self._cache:
                self._cache[key].response = response
                self._cache[key].created_at = time.time()
                self._cache[key].last_accessed = time.time()
                self._cache.move_to_end(key)
                return

            # Evict LRU entries if at capacity
            while len(self._cache) >= self._max_size:
                oldest_key, _ = self._cache.popitem(last=False)  # Remove first (LRU)
                self._evictions += 1
                logger.debug("Cache evicted: {key}", key=oldest_key[:8])

            # Insert new entry
            now = time.time()
            self._cache[key] = CacheEntry(
                key=key,
                response=response,
                created_at=now,
                last_accessed=now,
            )
```

### Step 6: Implementasi `invalidate()` dan `clear()`
```python
    def invalidate(self, key: str) -> bool:
        """
        Remove a specific entry from the cache.

        Args:
            key: SHA-256 cache key to remove.

        Returns:
            True if entry was found and removed, False otherwise.
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> int:
        """
        Remove all entries from the cache.

        Returns:
            Number of entries that were removed.
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info("Cache cleared: {count} entries removed", count=count)
            return count
```

### Step 7: Implementasi `get_stats()` dan `is_enabled`
```python
    def get_stats(self) -> CacheStats:
        """
        Get current cache statistics.

        Returns:
            CacheStats with hit rate, size, and eviction count.
        """
        total = self._hits + self._misses
        return CacheStats(
            total_hits=self._hits,
            total_misses=self._misses,
            hit_rate=self._hits / total if total > 0 else 0.0,
            current_size=len(self._cache),
            max_size=self._max_size,
            evictions=self._evictions,
        )

    @property
    def is_enabled(self) -> bool:
        """Whether caching is enabled."""
        return self._enabled
```

## 6. Output yang Diharapkan

Verifikasi manual:
```python
from app.services.cache_service import CacheService

cache = CacheService(enabled=True, ttl=60, max_size=3)

# make_key — deterministic
key1 = CacheService.make_key("ollama", "llama3.2", "Apa itu AI?")
key2 = CacheService.make_key("ollama", "llama3.2", "Apa itu AI?")
key3 = CacheService.make_key("ollama", "llama3.2", "Apa itu ML?")
assert key1 == key2  # Same input → same key
assert key1 != key3  # Different input → different key
assert len(key1) == 64  # SHA-256 = 64 hex chars

# put + get
cache.put(key1, {"output": "AI adalah..."})
result = cache.get(key1)
assert result == {"output": "AI adalah..."}

# miss
assert cache.get("nonexistent") is None

# stats
stats = cache.get_stats()
assert stats.total_hits == 1
assert stats.total_misses == 1
assert stats.current_size == 1

# eviction (max_size=3)
cache.put(CacheService.make_key("a", "b", "1"), {"output": "1"})
cache.put(CacheService.make_key("a", "b", "2"), {"output": "2"})
cache.put(CacheService.make_key("a", "b", "3"), {"output": "3"})  # Evicts oldest
assert cache.get_stats().current_size == 3
assert cache.get_stats().evictions == 1

# clear
count = cache.clear()
assert count == 3
assert cache.get_stats().current_size == 0

print("All checks passed!")
```

## 7. Dependencies
- **Task 1** — `CacheEntry` dan `CacheStats` dataclasses

## 8. Acceptance Criteria
- [ ] `CacheService.__init__()` — OrderedDict, Lock, counters initialized
- [ ] `make_key()` — SHA-256 hash, deterministic, 64 hex chars
- [ ] `make_key()` — same inputs → same key, different inputs → different key
- [ ] `make_key()` — images hashed with MD5 and sorted for deterministic order
- [ ] `make_key()` — prompt whitespace stripped
- [ ] `get()` — cache hit → returns response, updates last_accessed, increments hit_count, moves to end
- [ ] `get()` — cache miss → returns None, increments misses
- [ ] `get()` — TTL expired → removes entry, returns None, counts as miss
- [ ] `get()` — disabled → always returns None
- [ ] `put()` — stores new entry with timestamps
- [ ] `put()` — existing key → updates response and timestamps
- [ ] `put()` — full cache → evicts LRU (oldest in OrderedDict), increments evictions
- [ ] `put()` — disabled → no-op
- [ ] `invalidate()` — removes specific entry, returns bool
- [ ] `clear()` — removes all, returns count
- [ ] `get_stats()` — accurate hits, misses, hit_rate, size, evictions
- [ ] `is_enabled` — property returns enabled state
- [ ] All operations thread-safe (Lock)
- [ ] Server bisa start tanpa error

## 9. Estimasi
Medium (~45 menit)
