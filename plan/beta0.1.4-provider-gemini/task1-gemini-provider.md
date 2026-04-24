# Task 1 — GeminiProvider Implementation

> **Modul**: beta0.1.4 — Gemini Provider  
> **Estimasi**: High (2–3 jam)  
> **Dependencies**: beta0.1.3 Task 1 (BaseProvider)

---

## 1. Judul Task

Implementasi `app/providers/gemini.py` — GeminiProvider yang menggunakan `google-genai` SDK untuk text generation via Google Gemini API.

---

## 2. Deskripsi

Membuat implementasi kedua dari `BaseProvider` yang terhubung ke Google Gemini API menggunakan official `google-genai` SDK. Untuk versi ini hanya `generate()` yang fully implemented — `stream()` dan `embedding()` di-stub. Error handling harus menangkap SDK exceptions dan wrap ke custom exception hierarchy.

---

## 3. Tujuan Teknis

- Class `GeminiProvider` extends `BaseProvider`
- Menggunakan `google.genai.Client` dari SDK resmi Google
- `generate()`: call `client.models.generate_content()`, parse `response.text`, normalize output
- Error handling: API errors → `ProviderAPIError`, timeout → `ProviderTimeoutError`
- `stream()` dan `embedding()`: raise `NotImplementedError`
- `supports_image()`: return `False` (enabled di beta0.1.7)
- `close()`: no-op (SDK manages connections)

---

## 4. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/providers/gemini.py`
- Method `generate()` fully functional
- Error handling untuk SDK exceptions

### ❌ Yang Tidak Dikerjakan

- `stream()` → beta0.1.5
- `embedding()` → beta0.1.6
- Image/multimodal support → beta0.1.7

---

## 5. Langkah Implementasi

### Step 1: Buat `app/providers/gemini.py`

```python
"""
Google Gemini AI provider implementation.

Connects to Google Gemini API via the official google-genai SDK.
See: https://ai.google.dev/gemini-api/docs

SDK package: google-genai
"""

from typing import AsyncGenerator, Optional

from loguru import logger

from app.core.exceptions import (
    ProviderAPIError,
    ProviderConnectionError,
    ProviderTimeoutError,
)
from app.providers.base import BaseProvider

try:
    from google import genai
    from google.genai import types
except ImportError:
    raise ImportError(
        "google-genai package not installed. "
        "Install with: pip install google-genai"
    )


class GeminiProvider(BaseProvider):
    """
    Provider implementation for Google Gemini.

    Uses the official google-genai SDK for all API interactions.
    The SDK handles authentication, retries, and connection management.
    """

    def __init__(self, api_key: str, timeout: int = 120):
        """
        Initialize GeminiProvider.

        Args:
            api_key: Google Gemini API key.
            timeout: Request timeout in seconds.
        """
        self._api_key = api_key
        self._timeout = timeout
        self._client = genai.Client(api_key=api_key)
        logger.info(
            "GeminiProvider initialized (timeout={timeout}s)",
            timeout=timeout,
        )

    @property
    def name(self) -> str:
        return "gemini"

    async def generate(
        self,
        model: str,
        prompt: str,
        images: Optional[list[str]] = None,
    ) -> dict:
        """
        Generate text using Gemini's generate_content API.

        For this version, only text input is supported.
        Image support will be added in beta0.1.7.

        SDK call:
            client.models.generate_content(
                model="gemini-2.0-flash",
                contents=["Hello"]
            )

        Response:
            response.text → "Hello! How can I help you?"
            response.usage_metadata → token counts
        """
        # Build contents — text only for now
        contents: list = [prompt]

        # Image support placeholder (beta0.1.7)
        if images:
            contents = [prompt]  # Will add image Parts in beta0.1.7

        try:
            response = self._client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    http_options=types.HttpOptions(
                        timeout=self._timeout * 1000,  # SDK uses milliseconds
                    ),
                ),
            )
        except Exception as e:
            error_str = str(e)

            # Timeout detection
            if "timeout" in error_str.lower() or "deadline" in error_str.lower():
                raise ProviderTimeoutError(
                    provider=self.name,
                    timeout=self._timeout,
                )

            # Connection error detection
            if "connect" in error_str.lower() or "network" in error_str.lower():
                raise ProviderConnectionError(
                    provider=self.name,
                    detail=error_str[:200],
                )

            # Rate limiting and other API errors
            # Try to extract status code from error
            status_code = 500
            if hasattr(e, "status_code"):
                status_code = e.status_code
            elif hasattr(e, "code"):
                status_code = e.code
            elif "429" in error_str:
                status_code = 429
            elif "403" in error_str:
                status_code = 403
            elif "404" in error_str:
                status_code = 404

            raise ProviderAPIError(
                provider=self.name,
                status=status_code,
                detail=error_str[:200],
            )

        # Extract output text
        output_text = ""
        try:
            output_text = response.text or ""
        except Exception:
            # Some responses may not have text (e.g. safety blocked)
            if response.candidates:
                parts = response.candidates[0].content.parts
                output_text = "".join(p.text for p in parts if hasattr(p, "text"))

        # Extract usage metadata
        usage = {}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            um = response.usage_metadata
            usage = {
                "prompt_tokens": getattr(um, "prompt_token_count", None),
                "completion_tokens": getattr(um, "candidates_token_count", None),
                "total_tokens": getattr(um, "total_token_count", None),
            }

        return {
            "output": output_text,
            "model": model,
            "provider": self.name,
            "usage": usage or None,
            "metadata": None,
        }

    async def stream(
        self,
        model: str,
        prompt: str,
        images: Optional[list[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming generation — will be implemented in beta0.1.5."""
        raise NotImplementedError(
            "GeminiProvider.stream() not yet implemented. See beta0.1.5."
        )
        yield ""  # pragma: no cover

    async def embedding(
        self,
        model: str,
        input_text: str,
    ) -> list[float]:
        """Embedding generation — will be implemented in beta0.1.6."""
        raise NotImplementedError(
            "GeminiProvider.embedding() not yet implemented. See beta0.1.6."
        )

    def supports_image(self, model: str) -> bool:
        """Image support — will be enabled in beta0.1.7."""
        return False

    async def close(self) -> None:
        """
        No-op — google-genai SDK manages its own connections.
        """
        logger.debug("GeminiProvider close (no-op, SDK managed)")
```

### Step 2: Verifikasi (unit — tanpa API key)

```bash
python -c "
from app.providers.gemini import GeminiProvider
from app.providers.base import BaseProvider

# Note: will fail if no valid API key, but class creation should work
provider = GeminiProvider(api_key='test-key', timeout=30)
print(f'Name: {provider.name}')
print(f'Is BaseProvider: {isinstance(provider, BaseProvider)}')
print(f'Supports image: {provider.supports_image(\"gemini-2.0-flash\")}')
"
```

Output:

```
Name: gemini
Is BaseProvider: True
Supports image: False
```

### Step 3: Verifikasi (integration — GEMINI_API_KEY diperlukan)

```bash
python -c "
import asyncio
from app.config import settings
from app.providers.gemini import GeminiProvider

async def test():
    if not settings.GEMINI_API_KEY:
        print('GEMINI_API_KEY not set, skipping integration test')
        return

    provider = GeminiProvider(
        api_key=settings.GEMINI_API_KEY,
        timeout=60,
    )
    result = await provider.generate(
        model='gemini-2.0-flash',
        prompt='Say hello in one word',
    )
    print(f'Output: {result[\"output\"][:100]}')
    print(f'Provider: {result[\"provider\"]}')
    print(f'Usage: {result[\"usage\"]}')

asyncio.run(test())
"
```

### Step 4: Test error handling (invalid API key)

```bash
python -c "
import asyncio
from app.providers.gemini import GeminiProvider
from app.core.exceptions import ProviderAPIError

async def test():
    provider = GeminiProvider(api_key='invalid-key', timeout=10)
    try:
        await provider.generate(model='gemini-2.0-flash', prompt='hi')
    except ProviderAPIError as e:
        print(f'Error: {e.message}')
        print(f'Code: {e.code}')

asyncio.run(test())
"
```

Output:

```
Error: Provider 'gemini' error (HTTP 403): ...
Code: PROVIDER_API_ERROR
```

---

## 6. Output yang Diharapkan

### File: `app/providers/gemini.py`

Isi seperti Step 1 di atas.

### generate() Return Format

```python
{
    "output": "Hello! How can I help you today?",
    "model": "gemini-2.0-flash",
    "provider": "gemini",
    "usage": {
        "prompt_tokens": 5,
        "completion_tokens": 8,
        "total_tokens": 13
    },
    "metadata": None
}
```

---

## 7. Dependencies

- **beta0.1.3 Task 1** — `BaseProvider` dari `app/providers/base.py`
- **beta0.1.1 Task 3** — Exception classes
- **Package**: `google-genai` harus terinstall

---

## 8. Acceptance Criteria

- [ ] File `app/providers/gemini.py` ada
- [ ] `GeminiProvider` inherits `BaseProvider`
- [ ] `provider.name` == `"gemini"`
- [ ] `generate()` berhasil call Gemini API (jika API key valid)
- [ ] Response di-normalize ke format standard (output, model, provider, usage, metadata)
- [ ] Invalid API key → raise `ProviderAPIError`
- [ ] Timeout → raise `ProviderTimeoutError`
- [ ] Rate limit (429) → raise `ProviderAPIError` with status
- [ ] `stream()` → raise `NotImplementedError`
- [ ] `embedding()` → raise `NotImplementedError`
- [ ] `supports_image()` → return `False`
- [ ] `close()` → no-op (no error)

---

## 9. Estimasi

**High** — SDK integration, error classification from opaque exceptions, response extraction with multiple fallback paths.
