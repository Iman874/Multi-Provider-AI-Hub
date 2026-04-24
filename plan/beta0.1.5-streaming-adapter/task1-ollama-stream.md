# Task 1 — OllamaProvider.stream()

> **Modul**: beta0.1.5 — Streaming Adapter  
> **Estimasi**: High (2–3 jam)  
> **Dependencies**: beta0.1.3 Task 2 (OllamaProvider existing)

---

## 1. Judul Task

Implementasi `OllamaProvider.stream()` — replace stub dengan real NDJSON stream parsing dari Ollama API.

---

## 2. Deskripsi

Mengganti `NotImplementedError` stub di `OllamaProvider.stream()` dengan implementasi nyata yang melakukan HTTP POST ke `/api/generate` dengan `stream: true`, lalu mem-parse response NDJSON (newline-delimited JSON) line by line dan yield setiap token sebagai string.

---

## 3. Tujuan Teknis

- `stream()` menghasilkan `AsyncGenerator[str, None]` — yield token satu per satu
- POST ke `/api/generate` dengan `stream: true` di httpx
- Iterate response lines sebagai NDJSON
- Parse setiap line → extract field `response` → yield
- Stop saat `done: true`
- Error handling: timeout, connection error, malformed JSON

---

## 4. Scope

### ✅ Yang Dikerjakan

- Replace `stream()` stub di `app/providers/ollama.py`

### ❌ Yang Tidak Dikerjakan

- Streaming + image (beta0.1.7)
- SSE wrapping (itu di endpoint layer — task 4)
- GeneratorService.stream() (task 3)

---

## 5. Langkah Implementasi

### Step 1: Update `stream()` di `app/providers/ollama.py`

Replace stub method dengan implementasi berikut:

```python
    async def stream(
        self,
        model: str,
        prompt: str,
        images: Optional[list[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream tokens from Ollama's /api/generate endpoint.

        Ollama streams via NDJSON (newline-delimited JSON).
        Each line is a JSON object with a "response" field containing
        the next token, and a "done" field indicating completion.

        Example Ollama NDJSON lines:
            {"model":"llama3.2","response":"Hello","done":false}
            {"model":"llama3.2","response":" there","done":false}
            {"model":"llama3.2","response":"","done":true}
        """
        import json

        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": True,
        }

        # Image support placeholder (beta0.1.7)
        if images:
            payload["images"] = images

        try:
            async with self._client.stream(
                "POST",
                "/api/generate",
                json=payload,
            ) as response:
                if response.status_code != 200:
                    raise ProviderAPIError(
                        provider=self.name,
                        status=response.status_code,
                        detail=f"Stream request failed",
                    )

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning(
                            "Ollama stream: skipping malformed JSON line"
                        )
                        continue

                    # Check if generation is complete
                    if data.get("done", False):
                        break

                    # Extract and yield the token
                    token = data.get("response", "")
                    if token:
                        yield token

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
```

### Step 2: Pastikan import `json` ada di file

File `ollama.py` mungkin belum import `json`. Pastikan ada di top-level:

```python
import json
```

Atau bisa juga import di dalam method seperti contoh di atas.

### Step 3: Verifikasi (Ollama harus running)

```bash
python -c "
import asyncio
from app.providers.ollama import OllamaProvider

async def test():
    provider = OllamaProvider('http://localhost:11434', timeout=60)
    try:
        tokens = []
        async for token in provider.stream(model='llama3.2', prompt='Count 1 to 5'):
            tokens.append(token)
            print(f'Token: \"{token}\"')
        print(f'Total tokens: {len(tokens)}')
        print(f'Full text: {\"\" .join(tokens)}')
    finally:
        await provider.close()

asyncio.run(test())
"
```

Output yang diharapkan:

```
Token: "1"
Token: ","
Token: " 2"
Token: ","
Token: " 3"
...
Total tokens: ~15
Full text: 1, 2, 3, 4, 5
```

### Step 4: Test error handling

```bash
python -c "
import asyncio
from app.providers.ollama import OllamaProvider
from app.core.exceptions import ProviderConnectionError

async def test():
    provider = OllamaProvider('http://localhost:99999', timeout=5)
    try:
        async for token in provider.stream(model='test', prompt='hi'):
            print(token)
    except ProviderConnectionError as e:
        print(f'Error: {e.code} — {e.message}')

asyncio.run(test())
"
```

---

## 6. Output yang Diharapkan

### Method Behavior

```
OllamaProvider.stream("llama3.2", "Hello")
  → yield "Hello"
  → yield "!"
  → yield " How"
  → yield " can"
  → yield " I"
  → yield " help"
  → (done: true → stop)
```

### Ollama NDJSON → Token Mapping

| Ollama Line | Yielded Token |
|---|---|
| `{"response":"Hello","done":false}` | `"Hello"` |
| `{"response":" world","done":false}` | `" world"` |
| `{"response":"","done":true}` | *(stop, nothing yielded)* |

---

## 7. Dependencies

- **beta0.1.3 Task 2** — existing `OllamaProvider` class
- **Running Ollama** untuk integration test

---

## 8. Acceptance Criteria

- [ ] `stream()` no longer raises `NotImplementedError`
- [ ] `stream()` yields individual token strings
- [ ] Tokens match Ollama's `response` field
- [ ] `done: true` line stops iteration (no infinite loop)
- [ ] Malformed JSON lines are skipped (not crash)
- [ ] Empty `response` values are skipped
- [ ] Connection refused → raise `ProviderConnectionError`
- [ ] Timeout → raise `ProviderTimeoutError`
- [ ] HTTP non-200 → raise `ProviderAPIError`

---

## 9. Estimasi

**High** — HTTP streaming, NDJSON parsing, async generator, multiple error paths.
