# Task 1 — Image Utilities

> **Modul**: beta0.1.7 — Multimodal Handling  
> **Estimasi**: Medium (60–90 menit)  
> **Dependencies**: Tidak ada (standalone utility module)

---

## 1. Judul Task

Implementasi `app/utils/image.py` — Image processing utility functions untuk normalisasi format antara provider.

---

## 2. Deskripsi

Membuat module utility yang menangani semua operasi image yang dibutuhkan oleh provider layer. Ollama butuh pure base64 string (tanpa data URI prefix), Gemini butuh raw bytes + MIME type. Module ini menjembatani perbedaan itu.

---

## 3. Tujuan Teknis

- `strip_data_uri(base64_str)` → remove `data:image/...;base64,` prefix
- `detect_mime_type(base64_str)` → detect MIME dari data URI atau magic bytes
- `base64_to_bytes(base64_str)` → decode ke raw bytes
- `validate_image(base64_str)` → cek valid base64, cek ukuran ≤ 20MB
- Semua function harus handle edge cases (empty string, malformed data)

---

## 4. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/utils/image.py`
- Buat `app/utils/__init__.py` (jika belum ada)

### ❌ Yang Tidak Dikerjakan

- URL → base64 download (simpan sebagai future enhancement)
- Image resizing atau compression
- Image generation (text → image)

---

## 5. Langkah Implementasi

### Step 1: Buat `app/utils/__init__.py`

```python
"""Utility modules for AI Generative Core."""
```

### Step 2: Buat `app/utils/image.py`

```python
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
```

### Step 3: Verifikasi

```bash
python -c "
from app.utils.image import (
    strip_data_uri,
    detect_mime_type,
    base64_to_bytes,
    validate_image,
)
import base64

# 1. strip_data_uri
print('=== strip_data_uri ===')
result = strip_data_uri('data:image/jpeg;base64,ABC123')
print(f'With prefix: \"{result}\"')  # → ABC123

result2 = strip_data_uri('ABC123')
print(f'Without prefix: \"{result2}\"')  # → ABC123

# 2. detect_mime_type
print('\\n=== detect_mime_type ===')
print(detect_mime_type('data:image/png;base64,ABC'))  # → image/png

# Create a fake JPEG (starts with FF D8 FF)
fake_jpeg = base64.b64encode(b'\\xff\\xd8\\xff\\xe0' + b'\\x00' * 100).decode()
print(detect_mime_type(fake_jpeg))  # → image/jpeg

print(detect_mime_type('not-a-real-image'))  # → image/jpeg (default)

# 3. base64_to_bytes
print('\\n=== base64_to_bytes ===')
test = base64.b64encode(b'hello image').decode()
result = base64_to_bytes(f'data:image/png;base64,{test}')
print(f'Bytes: {result}')  # → b'hello image'

# 4. validate_image
print('\\n=== validate_image ===')
small_img = base64.b64encode(b'\\xff\\xd8\\xff' + b'\\x00' * 100).decode()
print(f'Valid: {validate_image(small_img)}')  # → True

try:
    validate_image('')
except ValueError as e:
    print(f'Empty: {e}')  # → Image data is empty
"
```

---

## 6. Output yang Diharapkan

### File: `app/utils/image.py`

Isi seperti Step 2 di atas.

### Function Summary

| Function | Input | Output |
|---|---|---|
| `strip_data_uri()` | `"data:image/jpeg;base64,ABC"` | `"ABC"` |
| `strip_data_uri()` | `"ABC"` | `"ABC"` |
| `detect_mime_type()` | `"data:image/png;base64,..."` | `"image/png"` |
| `detect_mime_type()` | raw base64 JPEG | `"image/jpeg"` |
| `base64_to_bytes()` | base64 string | `bytes` |
| `validate_image()` | valid base64 ≤ 20MB | `True` |
| `validate_image()` | empty string | `ValueError` |
| `validate_image()` | > 20MB | `ValueError` |

---

## 7. Dependencies

- Tidak ada dependency ke task lain (standalone utility)
- Standard library: `base64`, `re`

---

## 8. Acceptance Criteria

- [ ] File `app/utils/__init__.py` ada
- [ ] File `app/utils/image.py` ada
- [ ] `strip_data_uri()` removes data URI prefix correctly
- [ ] `strip_data_uri()` returns raw base64 unchanged
- [ ] `detect_mime_type()` detects from data URI prefix
- [ ] `detect_mime_type()` detects from magic bytes (JPEG, PNG, GIF, WEBP)
- [ ] `detect_mime_type()` defaults to `image/jpeg`
- [ ] `base64_to_bytes()` decodes with and without data URI prefix
- [ ] `base64_to_bytes()` raises `ValueError` for invalid base64
- [ ] `validate_image()` returns `True` for valid image
- [ ] `validate_image()` raises `ValueError` for empty input
- [ ] `validate_image()` raises `ValueError` for > 20MB
- [ ] `MAX_IMAGE_SIZE` constant is 20MB

---

## 9. Estimasi

**Medium** — Multiple utility functions with edge case handling and magic byte detection.
