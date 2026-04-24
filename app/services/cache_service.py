"""
Cache Service — In-memory response caching with TTL and LRU eviction.

Caches AI provider responses (generate + embedding) to reduce latency
and API quota usage. Uses SHA-256 hash keys for deterministic cache
lookups. Thread-safe via threading.Lock.
"""

import hashlib
import threading
import time
from collections import OrderedDict
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
