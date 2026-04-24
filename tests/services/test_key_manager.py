"""
Unit tests for KeyManager service.
"""

import time

import pytest

from app.core.exceptions import AllKeysExhaustedError
from app.services.key_manager import KeyManager


class TestKeyManagerRoundRobin:
    """Tests for round-robin key selection."""

    def test_round_robin_3_keys(self):
        """Keys rotate in order: A → B → C → A."""
        km = KeyManager("test", ["A", "B", "C"])
        assert km.get_key() == "A"
        assert km.get_key() == "B"
        assert km.get_key() == "C"
        assert km.get_key() == "A"  # wraps around

    def test_single_key(self):
        """Single key always returned."""
        km = KeyManager("test", ["only-key"])
        assert km.get_key() == "only-key"
        assert km.get_key() == "only-key"


class TestKeyManagerBlacklist:
    """Tests for blacklist/failure handling."""

    def test_blacklist_skip(self):
        """Blacklisted key is skipped."""
        km = KeyManager("test", ["A", "B", "C"], cooldown=60)
        km.report_failure("A")
        # A is blacklisted, should get B
        assert km.get_key() == "B"

    def test_cooldown_expire(self):
        """Blacklisted key returns after cooldown expires."""
        km = KeyManager("test", ["A", "B"], cooldown=1)
        km.report_failure("A")
        # A is blacklisted
        assert km.get_key() == "B"
        # Wait for cooldown
        time.sleep(1.1)
        # A should be back (index may vary, but A is available)
        keys_gotten = {km.get_key() for _ in range(3)}
        assert "A" in keys_gotten

    def test_all_exhausted(self):
        """All keys blacklisted raises AllKeysExhaustedError."""
        km = KeyManager("test", ["A", "B"], cooldown=60)
        km.report_failure("A")
        km.report_failure("B")
        with pytest.raises(AllKeysExhaustedError):
            km.get_key()

    def test_report_success_clears_blacklist(self):
        """report_success removes key from blacklist."""
        km = KeyManager("test", ["A", "B"], cooldown=60)
        km.report_failure("A")
        assert km.available_count == 1
        km.report_success("A")
        assert km.available_count == 2


class TestKeyManagerProperties:
    """Tests for properties and utilities."""

    def test_empty_pool(self):
        """Empty key pool raises on get_key."""
        km = KeyManager("test", [])
        assert km.has_keys is False
        assert km.total_count == 0
        with pytest.raises(AllKeysExhaustedError):
            km.get_key()

    def test_has_keys(self):
        """has_keys is True when keys exist."""
        km = KeyManager("test", ["A"])
        assert km.has_keys is True

    def test_total_count(self):
        """total_count returns number of keys."""
        km = KeyManager("test", ["A", "B", "C"])
        assert km.total_count == 3

    def test_available_count(self):
        """available_count excludes blacklisted keys."""
        km = KeyManager("test", ["A", "B", "C"], cooldown=60)
        assert km.available_count == 3
        km.report_failure("A")
        assert km.available_count == 2

    def test_mask_key(self):
        """mask_key shows only last 4 chars."""
        assert KeyManager.mask_key("abcdefghijkl") == "***ijkl"

    def test_mask_key_short(self):
        """mask_key handles short keys."""
        assert KeyManager.mask_key("ab") == "***ab"

    def test_whitespace_stripped(self):
        """Keys with whitespace are stripped on init."""
        km = KeyManager("test", ["  A  ", " B ", "C"])
        assert km.get_key() == "A"
        assert km.get_key() == "B"

    def test_empty_strings_filtered(self):
        """Empty strings in key list are filtered out."""
        km = KeyManager("test", ["A", "", "  ", "B"])
        assert km.total_count == 2
