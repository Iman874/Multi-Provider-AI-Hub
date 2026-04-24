# Task 2 — GeminiProvider.stream()

> **Modul**: beta0.1.5 — Streaming Adapter  
> **Estimasi**: Medium (60–90 menit)  
> **Dependencies**: beta0.1.4 Task 1 (GeminiProvider existing)

---

## 1. Judul Task

Implementasi `GeminiProvider.stream()` — replace stub dengan real streaming via `generate_content_stream()` SDK method.

---

## 2. Deskripsi

Mengganti `NotImplementedError` stub di `GeminiProvider.stream()` dengan implementasi nyata menggunakan `client.models.generate_content_stream()`. SDK mengembalikan iterable chunks — setiap chunk memiliki `.text` yang berisi token fragment.

---

## 3. Tujuan Teknis

- `stream()` menghasilkan `AsyncGenerator[str, None]` — yield token per chunk
- Call `client.models.generate_content_stream(model, contents)`
- Iterate chunks → extract `chunk.text` → yield
- Skip empty chunks
- Error handling: API error, timeout

---

## 4. Scope

### ✅ Yang Dikerjakan

- Replace `stream()` stub di `app/providers/gemini.py`

### ❌ Yang Tidak Dikerjakan

- Streaming + image (beta0.1.7)
- SSE endpoint (task 4)

---

## 5. Langkah Implementasi

### Step 1: Update `stream()` di `app/providers/gemini.py`

Replace stub method dengan implementasi berikut:

```python
    async def stream(
        self,
        model: str,
        prompt: str,
        images: Optional[list[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream tokens from Gemini's generate_content_stream API.

        The SDK returns an iterable of chunks. Each chunk has a .text
        attribute containing the next token fragment.

        Note: google-genai SDK's streaming is synchronous iteration.
        We wrap it in async context for compatibility with our async interface.
        """
        # Build contents — text only for now
        contents: list = [prompt]

        # Image support placeholder (beta0.1.7)
        if images:
            contents = [prompt]

        try:
            response = self._client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    http_options=types.HttpOptions(
                        timeout=self._timeout * 1000,
                    ),
                ),
            )

            for chunk in response:
                # Extract text from chunk
                token = ""
                try:
                    token = chunk.text or ""
                except Exception:
                    # Some chunks may not have text
                    if chunk.candidates:
                        parts = chunk.candidates[0].content.parts
                        token = "".join(
                            p.text for p in parts if hasattr(p, "text")
                        )

                if token:
                    yield token

        except Exception as e:
            error_str = str(e)

            if "timeout" in error_str.lower() or "deadline" in error_str.lower():
                raise ProviderTimeoutError(
                    provider=self.name,
                    timeout=self._timeout,
                )

            if "connect" in error_str.lower() or "network" in error_str.lower():
                raise ProviderConnectionError(
                    provider=self.name,
                    detail=error_str[:200],
                )

            status_code = 500
            if hasattr(e, "status_code"):
                status_code = e.status_code
            elif hasattr(e, "code"):
                status_code = e.code
            elif "429" in error_str:
                status_code = 429
            elif "403" in error_str:
                status_code = 403

            raise ProviderAPIError(
                provider=self.name,
                status=status_code,
                detail=error_str[:200],
            )
```

### Step 2: Verifikasi (GEMINI_API_KEY diperlukan)

```bash
python -c "
import asyncio
from app.config import settings
from app.providers.gemini import GeminiProvider

async def test():
    if not settings.GEMINI_API_KEY:
        print('GEMINI_API_KEY not set, skipping')
        return

    provider = GeminiProvider(
        api_key=settings.GEMINI_API_KEY,
        timeout=60,
    )
    tokens = []
    async for token in provider.stream(model='gemini-2.0-flash', prompt='Count 1 to 5'):
        tokens.append(token)
        print(f'Chunk: \"{token}\"')
    print(f'Total chunks: {len(tokens)}')
    print(f'Full text: {\"\" .join(tokens)}')

asyncio.run(test())
"
```

Output yang diharapkan:

```
Chunk: "1, "
Chunk: "2, 3"
Chunk: ", 4, 5"
Total chunks: 3
Full text: 1, 2, 3, 4, 5
```

> **Note**: Gemini chunks are larger than Ollama tokens — each chunk may contain multiple words.

### Step 3: Test error handling

```bash
python -c "
import asyncio
from app.providers.gemini import GeminiProvider
from app.core.exceptions import ProviderAPIError

async def test():
    provider = GeminiProvider(api_key='invalid-key', timeout=10)
    try:
        async for token in provider.stream(model='gemini-2.0-flash', prompt='hi'):
            print(token)
    except ProviderAPIError as e:
        print(f'Error: {e.code} — {e.message}')

asyncio.run(test())
"
```

---

## 6. Output yang Diharapkan

### Method Behavior

```
GeminiProvider.stream("gemini-2.0-flash", "Hello")
  → yield "Hello! "
  → yield "How can I"
  → yield " help you today?"
  → (iteration ends)
```

### Gemini Chunk → Token Mapping

| SDK Chunk | Yielded Token |
|---|---|
| `chunk.text = "Hello! "` | `"Hello! "` |
| `chunk.text = "How can I"` | `"How can I"` |
| `chunk.text = ""` | *(skipped)* |
| `chunk.text = " help?"` | `" help?"` |

---

## 7. Dependencies

- **beta0.1.4 Task 1** — existing `GeminiProvider` class
- **Valid GEMINI_API_KEY** untuk integration test

---

## 8. Acceptance Criteria

- [ ] `stream()` no longer raises `NotImplementedError`
- [ ] `stream()` yields token strings from Gemini SDK
- [ ] Empty chunks are skipped (no empty string yields)
- [ ] Invalid API key → raise `ProviderAPIError`
- [ ] Timeout → raise `ProviderTimeoutError`
- [ ] `types.HttpOptions` sets proper timeout
- [ ] Chunk text extraction has fallback path (candidates)

---

## 9. Estimasi

**Medium** — SDK iteration is simpler than raw HTTP, but error classification and chunk extraction need care.
