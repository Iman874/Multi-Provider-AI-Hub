"""
Unit tests for CacheService.

Tests cover: cache hit/miss, TTL expiry, LRU eviction,
key generation, invalidate, clear, stats, and disabled mode.
"""

import time
from unittest.mock import patch

import pytest

from app.services.cache_service import CacheService, CacheEntry, CacheStats


@pytest.fixture
def cache():
    """Create a CacheService with small limits for testing."""
    return CacheService(enabled=True, ttl=60, max_size=5)


@pytest.fixture
def disabled_cache():
    """Create a disabled CacheService."""
    return CacheService(enabled=False, ttl=60, max_size=5)


def test_cache_hit(cache: CacheService):
    """Test put then get → response returned (cache hit)."""
    key = CacheService.make_key("ollama", "llama3.2", "Hello")
    response = {"output": "Hi there!", "provider": "ollama", "model": "llama3.2"}

    cache.put(key, response)
    result = cache.get(key)

    assert result is not None
    assert result["output"] == "Hi there!"
    assert result["provider"] == "ollama"

    # Stats should show 1 hit
    stats = cache.get_stats()
    assert stats.total_hits == 1
    assert stats.total_misses == 0


def test_cache_miss(cache: CacheService):
    """Test get without put → None (cache miss)."""
    result = cache.get("nonexistent-key")

    assert result is None

    stats = cache.get_stats()
    assert stats.total_hits == 0
    assert stats.total_misses == 1


def test_ttl_expiry(cache: CacheService):
    """Test expired entry returns None and is removed (mock time)."""
    key = CacheService.make_key("ollama", "llama3.2", "Hello")
    response = {"output": "Hi!"}

    cache.put(key, response)

    # Verify it's accessible now
    assert cache.get(key) is not None

    # Mock time to be 61 seconds later (past TTL of 60)
    future_time = time.time() + 61
    with patch("app.services.cache_service.time") as mock_time:
        mock_time.time.return_value = future_time
        result = cache.get(key)

    assert result is None  # Expired → miss

    stats = cache.get_stats()
    assert stats.total_misses == 1  # The expired get counts as miss
    assert stats.current_size == 0  # Entry was removed


def test_lru_eviction(cache: CacheService):
    """Test full cache → oldest (least recently used) entry is evicted."""
    # cache has max_size=5
    keys = []
    for i in range(5):
        key = CacheService.make_key("ollama", "llama3.2", f"prompt-{i}")
        cache.put(key, {"output": f"response-{i}"})
        keys.append(key)

    # Cache should be full
    assert cache.get_stats().current_size == 5

    # Add one more → should evict the first (LRU)
    new_key = CacheService.make_key("ollama", "llama3.2", "prompt-new")
    cache.put(new_key, {"output": "new response"})

    # Size should still be 5 (not 6)
    assert cache.get_stats().current_size == 5

    # First key should be evicted
    assert cache.get(keys[0]) is None

    # New key should be accessible
    assert cache.get(new_key) is not None

    # Eviction counter
    assert cache.get_stats().evictions == 1


def test_make_key_deterministic():
    """Test same inputs always produce the same cache key."""
    key1 = CacheService.make_key("ollama", "llama3.2", "Hello world")
    key2 = CacheService.make_key("ollama", "llama3.2", "Hello world")

    assert key1 == key2
    assert len(key1) == 64  # SHA-256 = 64 hex chars


def test_make_key_different_prompt():
    """Test different prompts produce different cache keys."""
    key1 = CacheService.make_key("ollama", "llama3.2", "Apa itu AI?")
    key2 = CacheService.make_key("ollama", "llama3.2", "Apa itu ML?")

    assert key1 != key2


def test_make_key_different_model():
    """Test different models produce different cache keys (even same prompt)."""
    key1 = CacheService.make_key("ollama", "llama3.2", "Hello")
    key2 = CacheService.make_key("ollama", "mistral", "Hello")

    assert key1 != key2


def test_invalidate(cache: CacheService):
    """Test invalidating a specific cache entry."""
    key = CacheService.make_key("ollama", "llama3.2", "Hello")
    cache.put(key, {"output": "Hi!"})

    # Should exist
    assert cache.get(key) is not None

    # Invalidate
    result = cache.invalidate(key)
    assert result is True

    # Should no longer exist
    assert cache.get(key) is None

    # Invalidating non-existent key
    result2 = cache.invalidate("nonexistent")
    assert result2 is False


def test_clear(cache: CacheService):
    """Test clearing all cache entries returns count."""
    # Add 3 entries
    for i in range(3):
        key = CacheService.make_key("ollama", "llama3.2", f"prompt-{i}")
        cache.put(key, {"output": f"response-{i}"})

    assert cache.get_stats().current_size == 3

    # Clear
    count = cache.clear()
    assert count == 3
    assert cache.get_stats().current_size == 0

    # Clear empty cache
    count2 = cache.clear()
    assert count2 == 0


def test_stats_accuracy(cache: CacheService):
    """Test cache stats accurately track hits, misses, and hit rate."""
    key = CacheService.make_key("ollama", "llama3.2", "Hello")
    cache.put(key, {"output": "Hi!"})

    # 2 hits
    cache.get(key)
    cache.get(key)

    # 1 miss
    cache.get("nonexistent")

    stats = cache.get_stats()
    assert stats.total_hits == 2
    assert stats.total_misses == 1
    assert stats.hit_rate == pytest.approx(2 / 3, rel=1e-2)
    assert stats.current_size == 1


def test_disabled_cache(disabled_cache: CacheService):
    """Test disabled cache: get always returns None, put is no-op."""
    assert disabled_cache.is_enabled is False

    key = CacheService.make_key("ollama", "llama3.2", "Hello")

    # put should be no-op
    disabled_cache.put(key, {"output": "Hi!"})
    assert disabled_cache.get_stats().current_size == 0

    # get should always return None
    result = disabled_cache.get(key)
    assert result is None


def test_put_updates_existing(cache: CacheService):
    """Test putting same key again updates the response (not duplicate)."""
    key = CacheService.make_key("ollama", "llama3.2", "Hello")

    # First put
    cache.put(key, {"output": "First response"})
    assert cache.get_stats().current_size == 1

    # Second put with same key → update
    cache.put(key, {"output": "Updated response"})
    assert cache.get_stats().current_size == 1  # Still 1, not 2

    # Should return updated response
    result = cache.get(key)
    assert result["output"] == "Updated response"
