# Task 4 — GeminiProvider Multi-Key

> **Modul**: beta0.1.9 — Multi API Key Management  
> **Estimasi**: Medium (60 menit)  
> **Dependencies**: Task 1, Task 2

---

## 1. Judul Task

Refactor `GeminiProvider` agar menggunakan `KeyManager` dengan round-robin key rotation dan retry otomatis saat rate limit (429).

---

## 2. Deskripsi

Saat ini `GeminiProvider` membuat satu `genai.Client` di `__init__` dengan satu API key. Task ini mengubahnya agar setiap request API membuat `genai.Client` lokal menggunakan key yang diambil dari `KeyManager`. Jika satu key kena rate limit (429), provider otomatis retry 1x dengan key berikutnya dari pool.

---

## 3. Tujuan Teknis

- `__init__()` menerima `key_manager: KeyManager` menggantikan `api_key: str`
- Hapus `self._client` global, buat client per-request via `_get_client()`
- Setiap method (`generate`, `stream`, `embedding`) gunakan client lokal
- Retry logic: 429 → blacklist key, coba 1x lagi dengan key baru
- Report success/failure ke `KeyManager`

---

## 4. Scope

### ✅ Yang Dikerjakan
- Edit `app/providers/gemini.py`
- Refactor constructor
- Helper `_get_client()`
- Retry logic untuk 429
- Update semua 3 method + `_build_contents()`

### ❌ Yang Tidak Dikerjakan
- Factory integration (Task 5)
- Testing (Task 6)

---

## 5. Langkah Implementasi

### Step 1: Update import

```python
from app.services.key_manager import KeyManager
```

### Step 2: Refactor `__init__()`

**Sebelum:**
```python
def __init__(self, api_key: str, timeout: int = 120):
    self._api_key = api_key
    self._timeout = timeout
    self._client = genai.Client(api_key=api_key)
```

**Sesudah:**
```python
def __init__(self, key_manager: KeyManager, timeout: int = 120):
    self._key_manager = key_manager
    self._timeout = timeout
    logger.info(
        "GeminiProvider initialized (timeout={timeout}s, keys={keys})",
        timeout=timeout,
        keys=key_manager.total_count,
    )
```

### Step 3: Buat helper `_get_client()`

```python
def _get_client(self) -> tuple:
    """
    Create a per-request genai.Client using the next available key.

    Returns:
        Tuple of (genai.Client, key_used_string)
    """
    key = self._key_manager.get_key()
    client = genai.Client(api_key=key)
    return client, key
```

### Step 4: Update `generate()` dengan retry logic

```python
async def generate(self, model, prompt, images=None):
    contents = self._build_contents(prompt, images)
    max_attempts = 2  # 1 normal + 1 retry

    for attempt in range(max_attempts):
        client, key = self._get_client()

        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    http_options=types.HttpOptions(
                        timeout=self._timeout * 1000,
                    ),
                ),
            )
        except Exception as e:
            error_str = str(e)

            # Check if rate limited (429)
            is_rate_limited = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str
            if is_rate_limited:
                self._key_manager.report_failure(key)
                if attempt < max_attempts - 1:
                    logger.warning(
                        "Gemini rate limited with key {masked}, retrying with next key",
                        masked=self._key_manager.mask_key(key),
                    )
                    continue  # retry with next key
                # Last attempt — raise

            # Other errors: timeout, connection, etc (existing logic)
            if "timeout" in error_str.lower() or "deadline" in error_str.lower():
                raise ProviderTimeoutError(provider=self.name, timeout=self._timeout)

            if "connect" in error_str.lower() or "network" in error_str.lower():
                raise ProviderConnectionError(provider=self.name, detail=error_str[:200])

            status_code = 500
            if hasattr(e, "status_code"): status_code = e.status_code
            elif hasattr(e, "code"): status_code = e.code
            elif "429" in error_str: status_code = 429
            elif "403" in error_str: status_code = 403
            elif "404" in error_str: status_code = 404

            raise ProviderAPIError(provider=self.name, status=status_code, detail=error_str[:200])

        # Success
        self._key_manager.report_success(key)

        # ... (existing response parsing — output_text, usage, return dict) ...
        # return { "output": ..., "model": ..., "provider": ..., "usage": ..., "metadata": ... }
```

### Step 5: Update `stream()` — sama pattern

```python
async def stream(self, model, prompt, images=None):
    contents = self._build_contents(prompt, images)

    # Untuk stream, retry di awal saja (sebelum mulai yield)
    client, key = self._get_client()

    try:
        response = client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                http_options=types.HttpOptions(timeout=self._timeout * 1000),
            ),
        )

        for chunk in response:
            # ... (existing token extraction) ...
            if token:
                yield token

        # Report success setelah stream selesai
        self._key_manager.report_success(key)

    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            self._key_manager.report_failure(key)
        # ... (existing error handling) ...
```

### Step 6: Update `embedding()` — sama pattern seperti generate (dengan retry)

```python
async def embedding(self, model, input_text):
    max_attempts = 2

    for attempt in range(max_attempts):
        client, key = self._get_client()

        try:
            result = client.models.embed_content(model=model, contents=input_text)
        except Exception as e:
            error_str = str(e)
            is_rate_limited = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str
            if is_rate_limited:
                self._key_manager.report_failure(key)
                if attempt < max_attempts - 1:
                    continue
            # ... (existing error handling) ...

        # Success
        self._key_manager.report_success(key)

        if not result.embeddings or not result.embeddings[0].values:
            raise ProviderAPIError(...)

        return list(result.embeddings[0].values)
```

---

## 6. Output yang Diharapkan

### Alur normal (key pool = [key-A, key-B, key-C]):
```
Request 1 → uses key-A → 200 OK → report_success(key-A)
Request 2 → uses key-B → 200 OK → report_success(key-B)
Request 3 → uses key-C → 200 OK → report_success(key-C)
Request 4 → uses key-A → (round-robin wraps)
```

### Alur rate limit (key-A kena 429):
```
Request 1 → uses key-A → 429 → report_failure(key-A) → retry → uses key-B → 200 OK
Request 2 → uses key-C (key-A di-skip karena blacklisted)
```

---

## 7. Dependencies

- **Task 1** — `AllKeysExhaustedError` di exceptions.py
- **Task 2** — `KeyManager` class

---

## 8. Acceptance Criteria

- [ ] `GeminiProvider(key_manager=km)` — constructor menerima `KeyManager`
- [ ] Setiap `generate()` call membuat `genai.Client` baru dari key pool
- [ ] Round-robin: 3 key → request dirotasi urut
- [ ] 429 error → `report_failure(key)`, retry 1x dengan key baru
- [ ] 429 pada retry terakhir → raise `ProviderAPIError` dengan status 429
- [ ] Semua key rate limited → `AllKeysExhaustedError` dari `get_key()`
- [ ] Non-429 error → raise langsung tanpa retry
- [ ] Success → `report_success(key)`
- [ ] Key TIDAK muncul di log (hanya masked via `mask_key()`)
- [ ] `stream()` dan `embedding()` mengikuti pattern yang sama

---

## 9. Estimasi

**Medium** — Refactor constructor + retry logic di 3 method, tapi polanya konsisten.
