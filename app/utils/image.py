"""
Image processing utilities for multimodal AI operations.

Handles the normalization of image formats between different providers:
- Ollama expects: pure base64 strings (no data URI prefix)
- Gemini expects: raw bytes + MIME type

All functions handle both data URI format and raw base64 input.
"""

import base64
import re

from loguru import logger


# Maximum image size in bytes (20MB)
MAX_IMAGE_SIZE = 20 * 1024 * 1024

# Data URI pattern: data:image/jpeg;base64,/9j/4AAQ...
DATA_URI_PATTERN = re.compile(
    r"^data:(?P<mime>image/[a-zA-Z0-9.+-]+);base64,(?P<data>.+)$",
    re.DOTALL,
)

# Magic bytes for common image formats
MAGIC_BYTES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"RIFF": "image/webp",  # RIFF....WEBP (check further bytes)
}


def strip_data_uri(base64_str: str) -> str:
    """
    Remove data URI prefix from a base64 image string.

    Input:  "data:image/jpeg;base64,/9j/4AAQ..."
    Output: "/9j/4AAQ..."

    If the string has no data URI prefix, it is returned as-is.

    Args:
        base64_str: Base64 image string, with or without data URI prefix.

    Returns:
        Pure base64 string without prefix.
    """
    match = DATA_URI_PATTERN.match(base64_str)
    if match:
        return match.group("data")
    return base64_str


def detect_mime_type(base64_str: str) -> str:
    """
    Detect the MIME type of a base64-encoded image.

    Detection order:
    1. Extract from data URI prefix (if present)
    2. Decode first bytes and check magic bytes
    3. Default to "image/jpeg"

    Args:
        base64_str: Base64 image string, with or without data URI prefix.

    Returns:
        MIME type string (e.g. "image/jpeg", "image/png").
    """
    # 1. Check data URI prefix
    match = DATA_URI_PATTERN.match(base64_str)
    if match:
        return match.group("mime")

    # 2. Check magic bytes
    try:
        raw = base64.b64decode(base64_str[:32])  # Decode just the header
        for magic, mime in MAGIC_BYTES.items():
            if raw.startswith(magic):
                # Special case: WEBP needs additional check
                if magic == b"RIFF" and len(raw) >= 12:
                    if raw[8:12] == b"WEBP":
                        return "image/webp"
                    continue
                return mime
    except Exception:
        pass

    # 3. Default
    logger.debug("Could not detect MIME type, defaulting to image/jpeg")
    return "image/jpeg"


def base64_to_bytes(base64_str: str) -> bytes:
    """
    Convert a base64 image string to raw bytes.

    Automatically strips data URI prefix if present.

    Args:
        base64_str: Base64 image string, with or without data URI prefix.

    Returns:
        Raw image bytes.

    Raises:
        ValueError: If the string is not valid base64.
    """
    pure_b64 = strip_data_uri(base64_str)

    try:
        return base64.b64decode(pure_b64)
    except Exception as e:
        raise ValueError(f"Invalid base64 image data: {e}")


def validate_image(base64_str: str) -> bool:
    """
    Validate that a string is a valid base64-encoded image within size limits.

    Checks:
    1. String is not empty
    2. String is valid base64
    3. Decoded size ≤ MAX_IMAGE_SIZE (20MB)

    Args:
        base64_str: Base64 image string to validate.

    Returns:
        True if valid.

    Raises:
        ValueError: If validation fails, with descriptive message.
    """
    if not base64_str or not base64_str.strip():
        raise ValueError("Image data is empty")

    try:
        raw_bytes = base64_to_bytes(base64_str)
    except ValueError:
        raise ValueError("Image data is not valid base64")

    if len(raw_bytes) > MAX_IMAGE_SIZE:
        size_mb = len(raw_bytes) / (1024 * 1024)
        raise ValueError(
            f"Image too large: {size_mb:.1f}MB (max {MAX_IMAGE_SIZE // (1024 * 1024)}MB)"
        )

    return True
