# Task 1 — OllamaProvider.embedding()

> **Modul**: beta0.1.6 — Embedding Endpoint  
> **Estimasi**: Medium (45–60 menit)  
> **Dependencies**: beta0.1.3 Task 2 (OllamaProvider existing)

---

## 1. Judul Task

Implementasi `OllamaProvider.embedding()` — replace stub dengan real embedding via Ollama `/api/embed` endpoint.

---

## 2. Deskripsi

Mengganti `NotImplementedError` stub di `OllamaProvider.embedding()` dengan implementasi nyata yang melakukan POST ke `/api/embed` dan return vector `list[float]`.

---

## 3. Tujuan Teknis

- `embedding()` return `list[float]` — embedding vector
- POST ke `/api/embed` dengan payload `{ model, input: text }`
- Parse response: `response["embeddings"][0]`
- Error handling: timeout, connection, API error

---

## 4. Scope

### ✅ Yang Dikerjakan

- Replace `embedding()` stub di `app/providers/ollama.py`

### ❌ Yang Tidak Dikerjakan

- Batch embedding (multiple texts)
- Embedding caching
- Dimensionality metadata

---

## 5. Langkah Implementasi

### Step 1: Update `embedding()` di `app/providers/ollama.py`

Replace stub method dengan implementasi berikut:

```python
    async def embedding(
        self,
        model: str,
        input_text: str,
    ) -> list[float]:
        """
        Generate embedding vector using Ollama's /api/embed endpoint.

        Ollama API request format:
            POST /api/embed
            { "model": "qwen3-embedding:0.6b", "input": "Hello world" }

        Ollama API response format:
            {
                "model": "qwen3-embedding:0.6b",
                "embeddings": [[0.0123, -0.0456, 0.0789, ...]]
            }
        """
        payload = {
            "model": model,
            "input": input_text,
        }

        try:
            response = await self._client.post(
                "/api/embed",
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

        # Extract first embedding vector
        embeddings = data.get("embeddings", [])
        if not embeddings or not embeddings[0]:
            raise ProviderAPIError(
                provider=self.name,
                status=200,
                detail="Empty embedding returned from Ollama",
            )

        return embeddings[0]
```

### Step 2: Verifikasi (Ollama harus running + qwen3-embedding:0.6b pulled)

```bash
python -c "
import asyncio
from app.providers.ollama import OllamaProvider

async def test():
    provider = OllamaProvider('http://localhost:11434', timeout=60)
    try:
        vector = await provider.embedding(
            model='qwen3-embedding:0.6b',
            input_text='Hello world',
        )
        print(f'Vector length: {len(vector)}')
        print(f'First 5 values: {vector[:5]}')
        print(f'Type: {type(vector[0])}')
    finally:
        await provider.close()

asyncio.run(test())
"
```

Output yang diharapkan:

```
Vector length: 1024
First 5 values: [0.0123, -0.0456, 0.0789, ...]
Type: <class 'float'>
```

### Step 3: Test error handling

```bash
python -c "
import asyncio
from app.providers.ollama import OllamaProvider
from app.core.exceptions import ProviderAPIError

async def test():
    provider = OllamaProvider('http://localhost:11434', timeout=60)
    try:
        # Model that doesn't exist
        await provider.embedding(model='nonexistent-embed', input_text='test')
    except ProviderAPIError as e:
        print(f'Error: {e.code} — {e.message}')
    finally:
        await provider.close()

asyncio.run(test())
"
```

---

## 6. Output yang Diharapkan

### Return Format

```python
[0.0123, -0.0456, 0.0789, 0.0234, -0.0567, ...]  # list[float], length varies by model
```

### Ollama API Mapping

| Ollama Response Field | Extracted Value |
|---|---|
| `embeddings[0]` | The full float vector |

### Vector Lengths (typical)

| Model | Dimension |
|---|---|
| `qwen3-embedding:0.6b` | 1024 |

---

## 7. Dependencies

- **beta0.1.3 Task 2** — existing `OllamaProvider` class
- **Running Ollama** with `qwen3-embedding:0.6b` model pulled (`ollama pull qwen3-embedding:0.6b`)

---

## 8. Acceptance Criteria

- [ ] `embedding()` no longer raises `NotImplementedError`
- [ ] `embedding()` returns `list[float]`
- [ ] Vector length > 0 (not empty)
- [ ] All values are `float` type
- [ ] POST to `/api/embed` with correct payload format
- [ ] Connection refused → raise `ProviderConnectionError`
- [ ] Timeout → raise `ProviderTimeoutError`
- [ ] HTTP non-200 → raise `ProviderAPIError`
- [ ] Empty embedding → raise `ProviderAPIError`

---

## 9. Estimasi

**Medium** — Simple HTTP call + response parsing, similar pattern to `generate()`.
