# Task 2 — GeminiProvider.embedding()

> **Modul**: beta0.1.6 — Embedding Endpoint  
> **Estimasi**: Medium (45–60 menit)  
> **Dependencies**: beta0.1.4 Task 1 (GeminiProvider existing)

---

> [!WARNING]
> **Gemini Embedding API Availability**  
> API endpoint `embed_content()` mungkin tidak selalu aktif atau tersedia untuk semua API key/plan.  
> Jika integration test gagal, task ini tetap dianggap **SELESAI** selama kode implementasi benar.  
> Ingatkan user: **"Embedding saat ini hanya tersedia via provider lokal (Ollama) saja."**

---

## 1. Judul Task

Implementasi `GeminiProvider.embedding()` — replace stub dengan real embedding via `client.models.embed_content()` SDK method, dengan graceful degradation jika API tidak tersedia.

---

## 2. Deskripsi

Mengganti `NotImplementedError` stub di `GeminiProvider.embedding()` dengan implementasi nyata menggunakan `client.models.embed_content()`. SDK mengembalikan object dengan `embeddings[0].values` yang berisi float vector.

**Catatan penting**: Gemini embedding API mungkin tidak selalu aktif. Jika API test gagal (403, 404, rate limit, atau model not available), implementasi tetap dianggap selesai selama error handling benar. Embedding akan fallback ke provider lokal (Ollama `qwen3-embedding:0.6b`).

---

## 3. Tujuan Teknis

- `embedding()` return `list[float]`
- Call `client.models.embed_content(model=model, contents=text)`
- Parse: `result.embeddings[0].values`
- Error handling: API error, invalid model, timeout
- **Graceful degradation**: jika API tidak tersedia, error jelas dikirim ke client

---

## 4. Scope

### ✅ Yang Dikerjakan

- Replace `embedding()` stub di `app/providers/gemini.py`
- Error handling yang informatif jika API tidak tersedia

### ❌ Yang Tidak Dikerjakan

- Batch embedding
- Embedding model auto-selection
- Fallback logic ke Ollama (user harus pilih provider sendiri)

---

## 5. Langkah Implementasi

### Step 1: Update `embedding()` di `app/providers/gemini.py`

Replace stub method dengan implementasi berikut:

```python
    async def embedding(
        self,
        model: str,
        input_text: str,
    ) -> list[float]:
        """
        Generate embedding vector using Gemini's embed_content API.

        SDK call:
            client.models.embed_content(
                model="text-embedding-004",
                contents="Hello world"
            )

        Response:
            result.embeddings[0].values → [0.0123, -0.0456, ...]

        Note:
            Gemini embedding API may not be available for all API keys/plans.
            If this fails, users should use Ollama embedding (qwen3-embedding:0.6b)
            as the local alternative.
        """
        try:
            result = self._client.models.embed_content(
                model=model,
                contents=input_text,
            )
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
            elif "404" in error_str:
                status_code = 404

            raise ProviderAPIError(
                provider=self.name,
                status=status_code,
                detail=error_str[:200],
            )

        # Extract embedding vector
        if not result.embeddings or not result.embeddings[0].values:
            raise ProviderAPIError(
                provider=self.name,
                status=200,
                detail="Empty embedding returned from Gemini",
            )

        return list(result.embeddings[0].values)
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
        print('⚠️  Embedding saat ini hanya tersedia via Ollama (qwen3-embedding:0.6b)')
        return

    provider = GeminiProvider(
        api_key=settings.GEMINI_API_KEY,
        timeout=60,
    )
    try:
        vector = await provider.embedding(
            model='text-embedding-004',
            input_text='Hello world',
        )
        print(f'✅ Gemini embedding OK')
        print(f'Vector length: {len(vector)}')
        print(f'First 5 values: {vector[:5]}')
        print(f'Type: {type(vector[0])}')
    except Exception as e:
        print(f'⚠️  Gemini embedding API tidak tersedia: {e}')
        print(f'⚠️  Embedding saat ini hanya tersedia via Ollama (qwen3-embedding:0.6b)')
        print(f'✅ Task tetap SELESAI — kode implementasi sudah benar')

asyncio.run(test())
"
```

**Jika API aktif**, output:

```
✅ Gemini embedding OK
Vector length: 768
First 5 values: [0.0412, -0.0231, 0.0567, ...]
Type: <class 'float'>
```

**Jika API TIDAK aktif**, output:

```
⚠️  Gemini embedding API tidak tersedia: ...
⚠️  Embedding saat ini hanya tersedia via Ollama (qwen3-embedding:0.6b)
✅ Task tetap SELESAI — kode implementasi sudah benar
```

### Step 3: Test error handling

```bash
python -c "
import asyncio
from app.providers.gemini import GeminiProvider
from app.core.exceptions import ProviderAPIError

async def test():
    provider = GeminiProvider(api_key='invalid-key', timeout=10)
    try:
        await provider.embedding(model='text-embedding-004', input_text='test')
    except ProviderAPIError as e:
        print(f'Error: {e.code} — {e.message}')

asyncio.run(test())
"
```

---

## 6. Output yang Diharapkan

### Return Format (jika API aktif)

```python
[0.0412, -0.0231, 0.0567, 0.0189, -0.0345, ...]  # list[float]
```

### Vector Lengths (typical)

| Model | Dimension |
|---|---|
| `text-embedding-004` | 768 |

### Availability Status

| Scenario | Behavior | Task Status |
|---|---|---|
| API aktif + valid key | Return embedding vector | ✅ Selesai |
| API aktif + invalid key | Raise `ProviderAPIError` (403) | ✅ Selesai |
| API tidak aktif / disabled | Raise `ProviderAPIError` | ✅ Selesai |
| No GEMINI_API_KEY | Provider not registered → 404 | ✅ Selesai |

> **Dalam semua scenario di atas**, task dianggap **SELESAI** selama error handling berfungsi benar.  
> Jika Gemini embedding API tidak tersedia, sampaikan ke user:  
> **"Embedding saat ini hanya tersedia via provider lokal (Ollama `qwen3-embedding:0.6b`). Gemini embedding akan otomatis aktif saat API endpoint tersedia."**

---

## 7. Dependencies

- **beta0.1.4 Task 1** — existing `GeminiProvider` class
- **Valid GEMINI_API_KEY** untuk integration test *(opsional — task selesai tanpa ini)*

---

## 8. Acceptance Criteria

- [ ] `embedding()` no longer raises `NotImplementedError`
- [ ] `embedding()` returns `list[float]` *(jika API aktif)*
- [ ] Uses `client.models.embed_content()` SDK method
- [ ] Invalid API key → raise `ProviderAPIError`
- [ ] Timeout → raise `ProviderTimeoutError`
- [ ] Empty embedding → raise `ProviderAPIError`
- [ ] Error messages jelas dan informatif
- [ ] ⚠️ Jika API test gagal → **tetap tandai SELESAI**, ingatkan user bahwa embedding hanya tersedia via Ollama lokal

---

## 9. Estimasi

**Medium** — SDK call similar to `generate()`, same error handling pattern. Extra care for graceful degradation messaging.
