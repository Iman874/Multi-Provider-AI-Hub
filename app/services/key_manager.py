"""
API Key pool manager for multi-key rotation.

Provides round-robin key selection with automatic blacklisting
for rate-limited keys. Provider-agnostic — used by any provider
that needs API key management.
"""

import time

from loguru import logger

from app.core.exceptions import AllKeysExhaustedError


class KeyManager:
    """
    Manages a pool of API keys with round-robin rotation
    and temporary blacklisting.

    Args:
        name: Human-readable label for logging (e.g. "gemini", "ollama_cloud").
        keys: List of API key strings.
        cooldown: Seconds to blacklist a key after failure (default: 60).
    """

    def __init__(self, name: str, keys: list[str], cooldown: int = 60):
        self._name = name
        self._keys = [k.strip() for k in keys if k.strip()]
        self._index = 0
        self._blacklist: dict[str, float] = {}  # key → expire_at timestamp
        self._cooldown = cooldown

        logger.info(
            "KeyManager '{name}' initialized: {count} key(s), cooldown={cooldown}s",
            name=name,
            count=len(self._keys),
            cooldown=cooldown,
        )

    @property
    def has_keys(self) -> bool:
        """Check if the pool has any keys at all."""
        return len(self._keys) > 0

    @property
    def total_count(self) -> int:
        """Total number of keys in the pool."""
        return len(self._keys)

    @property
    def available_count(self) -> int:
        """Number of keys not currently blacklisted."""
        now = time.time()
        blacklisted = sum(
            1 for expire_at in self._blacklist.values()
            if expire_at > now
        )
        return len(self._keys) - blacklisted

    @staticmethod
    def mask_key(key: str) -> str:
        """
        Mask an API key for safe logging.

        Shows only the last 4 characters:
            "abc123xyz789" → "***9789"
            "short" → "***hort"
        """
        if len(key) <= 4:
            return "***" + key
        return "***" + key[-4:]

    def get_key(self) -> str:
        """
        Get the next available API key using round-robin.

        Skips blacklisted keys (unless their cooldown has expired).
        Raises AllKeysExhaustedError if no keys are available.

        Returns:
            An API key string.
        """
        if not self._keys:
            raise AllKeysExhaustedError(provider=self._name)

        now = time.time()
        checked = 0

        while checked < len(self._keys):
            idx = self._index % len(self._keys)
            key = self._keys[idx]
            self._index = idx + 1  # advance for next call

            # Check blacklist
            if key in self._blacklist:
                if self._blacklist[key] > now:
                    # Still blacklisted — skip
                    checked += 1
                    continue
                else:
                    # Cooldown expired — remove from blacklist
                    del self._blacklist[key]
                    logger.debug(
                        "KeyManager '{name}': key {masked} cooldown expired, re-enabled",
                        name=self._name,
                        masked=self.mask_key(key),
                    )

            # Key is available
            logger.debug(
                "KeyManager '{name}': using key {masked}",
                name=self._name,
                masked=self.mask_key(key),
            )
            return key

        # All keys are blacklisted
        raise AllKeysExhaustedError(provider=self._name)

    def report_failure(self, key: str) -> None:
        """
        Temporarily blacklist a key after a failure (e.g. 429 rate limit).

        The key will be skipped for `cooldown` seconds, then automatically
        re-enabled on the next `get_key()` call.
        """
        expire_at = time.time() + self._cooldown
        self._blacklist[key] = expire_at
        logger.warning(
            "KeyManager '{name}': key {masked} blacklisted for {cooldown}s",
            name=self._name,
            masked=self.mask_key(key),
            cooldown=self._cooldown,
        )

    def report_success(self, key: str) -> None:
        """
        Clear a key from the blacklist after a successful request.

        This allows a previously-failed key to be used immediately
        on the next rotation cycle.
        """
        if key in self._blacklist:
            del self._blacklist[key]
            logger.debug(
                "KeyManager '{name}': key {masked} un-blacklisted after success",
                name=self._name,
                masked=self.mask_key(key),
            )
