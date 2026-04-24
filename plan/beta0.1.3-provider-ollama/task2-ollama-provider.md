# Task 2 — OllamaProvider (Text Generate)

> **Modul**: beta0.1.3 — Provider Abstraction & Ollama  
> **Estimasi**: High (2–4 jam)  
> **Dependencies**: Task 1 (Base Provider)

---

## 1. Judul Task

Implementasi `app/providers/ollama.py` — OllamaProvider yang connect ke Ollama lokal via HTTP dan mengimplementasi `generate()` untuk text generation.

---

## 2. Deskripsi

Membuat implementasi pertama dari `BaseProvider` yang terhubung ke Ollama API di localhost. Untuk versi ini hanya `generate()` yang fully implemented — `stream()` dan `embedding()` di-stub karena akan diimplementasi di beta0.1.5 dan 0.1.6. Error handling (timeout, connection refused) wajib ada.

---

## 3. Tujuan Teknis

- Class `OllamaProvider` extends `BaseProvider`
- Menggunakan `httpx.AsyncClient` untuk HTTP requests
- `generate()`: POST ke `/api/generate` dengan `stream: false`, parse response, normalize output
- Error handling: `ProviderTimeoutError`, `ProviderConnectionError`, `ProviderAPIError`
- `stream()` dan `embedding()`: raise `NotImplementedError` (stub)
- `supports_image()`: return `False` (akan di-enable di beta0.1.7)
- `close()`: close httpx client

---

## 4. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/providers/ollama.py`
- Method `generate()` fully functional
- Error handling untuk semua failure scenarios
- Method `close()` untuk cleanup

### ❌ Yang Tidak Dikerjakan

- `stream()` → beta0.1.5
- `embedding()` → beta0.1.6
- Image support → beta0.1.7
- Auto-discovery model dari Ollama API

---

## 5. Langkah Implementasi

### Step 1: Buat `app/providers/ollama.py`

```python
"""
Ollama AI provider implementation.

Connects to a local (or remote) Ollama instance via HTTP API.
See: https://github.com/ollama/ollama/blob/main/docs/api.md

Ollama API endpoints used:
- POST /api/generate  → text & multimodal generation
- POST /api/embed     → vector embedding (beta0.1.6)
- GET  /api/tags      → model listing (future)
"""

from typing import AsyncGenerator, Optional

import httpx
from loguru import logger

from app.core.exceptions import (
    ProviderAPIError,
    ProviderConnectionError,
    ProviderTimeoutError,
)
from app.providers.base import BaseProvider


class OllamaProvider(BaseProvider):
    """
    Provider implementation for Ollama (local LLM).

    Communicates with Ollama via its HTTP API using httpx.AsyncClient.
    """

    def __init__(self, base_url: str, timeout: int = 120):
        """
        Initialize OllamaProvider.

        Args:
            base_url: Ollama API base URL (e.g. "http://localhost:11434")
            timeout: Request timeout in seconds.
        """
        self._base_url = base_url
        self._timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(timeout),
        )
        logger.info(
            "OllamaProvider initialized: {url} (timeout={timeout}s)",
            url=base_url,
            timeout=timeout,
        )

    @property
    def name(self) -> str:
        return "ollama"

    async def generate(
        self,
        model: str,
        prompt: str,
        images: Optional[list[str]] = None,
    ) -> dict:
        """
        Generate text using Ollama's /api/generate endpoint.

        Sends a non-streaming request and returns the complete response.

        Ollama API request format:
            POST /api/generate
            { "model": "llama3.2", "prompt": "Hello", "stream": false }

        Ollama API response format:
            {
                "model": "llama3.2",
                "response": "Hi there!",
                "done": true,
                "total_duration": 1234567890,
                "prompt_eval_count": 5,
                "eval_count": 10
            }
        """
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }

        # Image support placeholder (will be enabled in beta0.1.7)
        if images:
            payload["images"] = images

        try:
            response = await self._client.post(
                "/api/generate",
                json=payload,
            )
        except httpx.TimeoutException:
            raise ProviderTimeoutError(
                provider=self.name,
                timeout=self._timeout,
            )
        except httpx.ConnectError:
            raise ProviderConnectionError(
                provider=self.name,
                detail=f"Connection refused at {self._base_url}",
            )

        if response.status_code != 200:
            raise ProviderAPIError(
                provider=self.name,
                status=response.status_code,
                detail=response.text[:200],
            )

        data = response.json()

        # Normalize to standard response format
        return {
            "output": data.get("response", ""),
            "model": data.get("model", model),
            "provider": self.name,
            "usage": {
                "prompt_tokens": data.get("prompt_eval_count"),
                "completion_tokens": data.get("eval_count"),
                "total_tokens": (
                    (data.get("prompt_eval_count") or 0)
                    + (data.get("eval_count") or 0)
                )
                or None,
            },
            "metadata": {
                "total_duration_ns": data.get("total_duration"),
                "load_duration_ns": data.get("load_duration"),
            },
        }

    async def stream(
        self,
        model: str,
        prompt: str,
        images: Optional[list[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming generation — will be implemented in beta0.1.5."""
        raise NotImplementedError(
            "OllamaProvider.stream() not yet implemented. See beta0.1.5."
        )
        # Required for AsyncGenerator type hint
        yield ""  # pragma: no cover

    async def embedding(
        self,
        model: str,
        input_text: str,
    ) -> list[float]:
        """Embedding generation — will be implemented in beta0.1.6."""
        raise NotImplementedError(
            "OllamaProvider.embedding() not yet implemented. See beta0.1.6."
        )

    def supports_image(self, model: str) -> bool:
        """Image support — will be enabled in beta0.1.7."""
        return False

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()
        logger.debug("OllamaProvider HTTP client closed")
```

### Step 2: Verifikasi (unit — tanpa Ollama running)

```bash
python -c "
from app.providers.ollama import OllamaProvider
from app.providers.base import BaseProvider

provider = OllamaProvider('http://localhost:11434', timeout=30)
print(f'Name: {provider.name}')
print(f'Is BaseProvider: {isinstance(provider, BaseProvider)}')
print(f'Supports image: {provider.supports_image(\"llama3.2\")}')
"
```

Output:

```
Name: ollama
Is BaseProvider: True
Supports image: False
```

### Step 3: Verifikasi (integration — Ollama harus running)

```bash
python -c "
import asyncio
from app.providers.ollama import OllamaProvider

async def test():
    provider = OllamaProvider('http://localhost:11434', timeout=60)
    try:
        result = await provider.generate(model='llama3.2', prompt='Say hello in one word')
        print(f'Output: {result[\"output\"][:100]}')
        print(f'Provider: {result[\"provider\"]}')
        print(f'Usage: {result[\"usage\"]}')
    finally:
        await provider.close()

asyncio.run(test())
"
```

### Step 4: Verifikasi error handling

```bash
python -c "
import asyncio
from app.providers.ollama import OllamaProvider
from app.core.exceptions import ProviderConnectionError

async def test():
    # Wrong URL → connection error
    provider = OllamaProvider('http://localhost:99999', timeout=5)
    try:
        await provider.generate(model='test', prompt='hi')
    except ProviderConnectionError as e:
        print(f'Connection error: {e.message}')
        print(f'Code: {e.code}')
    finally:
        await provider.close()

asyncio.run(test())
"
```

Output:

```
Connection error: Cannot connect to 'ollama': Connection refused at http://localhost:99999
Code: PROVIDER_CONNECTION_ERROR
```

---

## 6. Output yang Diharapkan

### File: `app/providers/ollama.py`

Isi seperti Step 1 di atas.

### generate() Return Format

```python
{
    "output": "Hi there! How can I help you today?",
    "model": "llama3.2",
    "provider": "ollama",
    "usage": {
        "prompt_tokens": 5,
        "completion_tokens": 12,
        "total_tokens": 17
    },
    "metadata": {
        "total_duration_ns": 1234567890,
        "load_duration_ns": 567890
    }
}
```

---

## 7. Dependencies

- **Task 1** — `BaseProvider` dari `app/providers/base.py`
- **beta0.1.1 Task 3** — Exception classes
- **Package**: `httpx` harus terinstall

---

## 8. Acceptance Criteria

- [ ] File `app/providers/ollama.py` ada
- [ ] `OllamaProvider` inherits `BaseProvider`
- [ ] `provider.name` == `"ollama"`
- [ ] `generate()` berhasil call Ollama API (jika Ollama running)
- [ ] Response di-normalize ke format standard (output, model, provider, usage, metadata)
- [ ] Connection refused → raise `ProviderConnectionError`
- [ ] Timeout → raise `ProviderTimeoutError`
- [ ] HTTP error (non-200) → raise `ProviderAPIError`
- [ ] `stream()` → raise `NotImplementedError`
- [ ] `embedding()` → raise `NotImplementedError`
- [ ] `supports_image()` → return `False`
- [ ] `close()` → close httpx client tanpa error

---

## 9. Estimasi

**High** — HTTP integration, response parsing, 3 error scenarios, async patterns.
