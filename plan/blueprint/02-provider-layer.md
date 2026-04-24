# 02 — Provider Layer Design

---

## Abstract Base Provider

File: `app/providers/base.py`

```python
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional

class BaseProvider(ABC):
    """
    Abstract contract yang WAJIB diimplementasi oleh semua provider.
    Menambah provider baru = buat class baru yang extend ini.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier: 'ollama', 'gemini', etc."""
        ...

    @abstractmethod
    async def generate(
        self,
        model: str,
        prompt: str,
        images: Optional[list[str]] = None,
    ) -> dict:
        """
        Generate text/multimodal response.

        Args:
            model: Model name (e.g. "llama3", "gemini-2.0-flash")
            prompt: Text input
            images: Optional list of base64-encoded images

        Returns:
            dict with keys: output, model, provider, usage, metadata
        """
        ...

    @abstractmethod
    async def stream(
        self,
        model: str,
        prompt: str,
        images: Optional[list[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream tokens via async generator.
        Each yield = one token/chunk string.
        """
        ...

    @abstractmethod
    async def embedding(
        self,
        model: str,
        input_text: str,
    ) -> list[float]:
        """
        Generate embedding vector from text.

        Returns:
            List of floats (embedding vector)
        """
        ...

    @abstractmethod
    def supports_image(self, model: str) -> bool:
        """Check if a specific model supports image/multimodal input."""
        ...

    async def close(self) -> None:
        """Cleanup resources (HTTP clients, etc). Override if needed."""
        pass
```

---

## OllamaProvider

File: `app/providers/ollama.py`

### API Endpoints Used

| Ollama API | Method | Purpose |
|---|---|---|
| `POST /api/generate` | generate + stream | Text & multimodal generation |
| `POST /api/embed` | embedding | Vector embedding |
| `GET /api/tags` | model listing | Discover available models |

### Implementation Notes

```python
class OllamaProvider(BaseProvider):
    """
    Connects to local Ollama instance via HTTP.
    Uses httpx.AsyncClient for all requests.
    """

    def __init__(self, base_url: str, timeout: int = 120):
        self._base_url = base_url
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout
        )

    @property
    def name(self) -> str:
        return "ollama"
```

### generate() Logic

```
1. Build payload: { model, prompt, stream: false }
2. If images provided → add "images": [base64_str, ...]
3. POST /api/generate
4. Parse response → normalize to standard format
5. Return: { output, model, provider, usage, metadata }
```

### stream() Logic

```
1. Build payload: { model, prompt, stream: true }
2. If images provided → add "images": [base64_str, ...]
3. POST /api/generate with stream=True
4. Iterate response lines (NDJSON)
5. Parse each line → yield token string
6. On "done": true → stop
```

### embedding() Logic

```
1. POST /api/embed with { model, input: text }
2. Parse response.embeddings[0]
3. Return float array
```

### Image Handling

- Ollama expects `images` as array of **base64-encoded strings** (no data URI prefix)
- Strip `data:image/...;base64,` prefix if present

---

## GeminiProvider

File: `app/providers/gemini.py`

### SDK Used

- `google-genai` (official Google Gen AI SDK)

### Implementation Notes

```python
class GeminiProvider(BaseProvider):
    """
    Connects to Google Gemini API via official SDK.
    """

    def __init__(self, api_key: str, timeout: int = 120):
        self._client = genai.Client(api_key=api_key)
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "gemini"
```

### generate() Logic

```
1. Build contents list:
   - Add text part: prompt
   - If images → add Image parts (base64 → Part.from_data)
2. client.models.generate_content(model=model, contents=contents)
3. Parse response.text
4. Normalize → { output, model, provider, usage, metadata }
```

### stream() Logic

```
1. Build contents (same as generate)
2. response = client.models.generate_content_stream(...)
3. for chunk in response:
     yield chunk.text
```

### embedding() Logic

```
1. client.models.embed_content(model=model, contents=text)
2. Return result.embeddings[0].values → float array
```

### Image Handling

- Gemini uses native multimodal via `Part.from_data(data=bytes, mime_type=...)`
- Convert base64 string → bytes before passing
- Supports: JPEG, PNG, WEBP, GIF

---

## Provider Factory

File: `app/providers/__init__.py`

```python
def create_provider(provider_name: str, settings) -> BaseProvider:
    """
    Factory function to instantiate provider by name.
    Used during app startup to register providers.
    """
    match provider_name:
        case "ollama":
            return OllamaProvider(
                base_url=settings.OLLAMA_BASE_URL,
                timeout=settings.OLLAMA_TIMEOUT,
            )
        case "gemini":
            return GeminiProvider(
                api_key=settings.GEMINI_API_KEY,
                timeout=settings.GEMINI_TIMEOUT,
            )
        case _:
            raise ValueError(f"Unknown provider: {provider_name}")
```

---

## Adding a New Provider (Checklist)

1. Create `app/providers/new_provider.py`
2. Implement `BaseProvider` (all 4 abstract methods)
3. Add case to `create_provider()` factory
4. Add config to `Settings` class
5. Register models di `ModelRegistry`
6. **Zero changes** to endpoints or services

> **Next**: See [03-service-layer.md](./03-service-layer.md)
