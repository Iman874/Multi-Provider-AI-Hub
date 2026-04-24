# Task 3 — OllamaProvider Cloud Auth

> **Modul**: beta0.1.9 — Multi API Key Management  
> **Estimasi**: Medium (45 menit)  
> **Dependencies**: Task 1, Task 2

---

## 1. Judul Task

Menambahkan dukungan `Authorization` header di `OllamaProvider` untuk model cloud, menggunakan key dari `KeyManager`.

---

## 2. Deskripsi

`OllamaProvider` saat ini mengirim request HTTP tanpa header autentikasi. Model cloud di Ollama (suffix `:cloud`) membutuhkan header `Authorization: Bearer <key>`. Task ini memodifikasi provider agar menyisipkan header auth secara otomatis jika `KeyManager` tersedia dan memiliki key, sambil memastikan model lokal tetap berjalan tanpa perubahan apapun.

---

## 3. Tujuan Teknis

- `OllamaProvider.__init__()` menerima parameter `key_manager: Optional[KeyManager]`
- Helper `_get_auth_headers()` menentukan apakah header auth diperlukan
- Method `generate()`, `stream()`, `embedding()` mengirim header auth jika ada key
- Key di-report ke `KeyManager` (success/failure) setelah response
- Model lokal tanpa key → zero-regression

---

## 4. Scope

### ✅ Yang Dikerjakan
- Edit `app/providers/ollama.py`
- Tambah parameter `key_manager` di constructor
- Tambah method `_get_auth_headers()`
- Update `generate()`, `stream()`, `embedding()` untuk kirim header
- Report success/failure ke KeyManager

### ❌ Yang Tidak Dikerjakan
- Factory integration (Task 5)
- Testing (Task 6)

---

## 5. Langkah Implementasi

### Step 1: Update import

Di bagian atas `ollama.py`, tambahkan:

```python
from typing import AsyncGenerator, Optional

# (existing imports...)

from app.services.key_manager import KeyManager
```

### Step 2: Update `__init__()`

```python
def __init__(
    self,
    base_url: str,
    timeout: int = 120,
    key_manager: Optional[KeyManager] = None,  # ← BARU
):
    self._base_url = base_url
    self._timeout = timeout
    self._key_manager = key_manager  # ← BARU
    self._client = httpx.AsyncClient(
        base_url=base_url,
        timeout=httpx.Timeout(timeout),
    )
    logger.info(
        "OllamaProvider initialized: {url} (timeout={timeout}s, cloud_keys={keys})",
        url=base_url,
        timeout=timeout,
        keys=key_manager.total_count if key_manager else 0,
    )
```

### Step 3: Tambah helper `_get_auth_headers()`

```python
def _get_auth_headers(self) -> tuple[dict, str | None]:
    """
    Get auth headers for the request.

    Returns:
        Tuple of (headers_dict, key_used).
        headers_dict: {"Authorization": "Bearer ..."} or {}
        key_used: the key string (for report_success/failure), or None
    """
    if self._key_manager and self._key_manager.has_keys:
        key = self._key_manager.get_key()
        return {"Authorization": f"Bearer {key}"}, key
    return {}, None
```

### Step 4: Update `generate()`

Perubahan pada method `generate()`:

```python
async def generate(self, model, prompt, images=None):
    # ... (payload setup tetap sama) ...

    # Ambil auth headers
    headers, key_used = self._get_auth_headers()

    try:
        response = await self._client.post(
            "/api/generate",
            json=payload,
            headers=headers,  # ← BARU
        )
    except httpx.TimeoutException:
        raise ProviderTimeoutError(...)
    except httpx.ConnectError:
        raise ProviderConnectionError(...)

    if response.status_code != 200:
        # Report failure jika pakai key dan kena rate limit
        if key_used and response.status_code in (401, 429):
            self._key_manager.report_failure(key_used)
        raise ProviderAPIError(...)

    # Report success jika pakai key
    if key_used:
        self._key_manager.report_success(key_used)

    # ... (response parsing tetap sama) ...
```

### Step 5: Update `stream()`

Pola yang sama:
```python
async def stream(self, model, prompt, images=None):
    # ... (payload setup tetap sama) ...

    headers, key_used = self._get_auth_headers()

    try:
        async with self._client.stream(
            "POST",
            "/api/generate",
            json=payload,
            headers=headers,  # ← BARU
        ) as response:
            if response.status_code != 200:
                if key_used and response.status_code in (401, 429):
                    self._key_manager.report_failure(key_used)
                raise ProviderAPIError(...)

            # Report success setelah stream dimulai
            if key_used:
                self._key_manager.report_success(key_used)

            # ... (token iteration tetap sama) ...
    except httpx.TimeoutException:
        raise ProviderTimeoutError(...)
    except httpx.ConnectError:
        raise ProviderConnectionError(...)
```

### Step 6: Update `embedding()`

Pola yang sama:
```python
async def embedding(self, model, input_text):
    # ... (payload setup tetap sama) ...

    headers, key_used = self._get_auth_headers()

    try:
        response = await self._client.post(
            "/api/embed",
            json=payload,
            headers=headers,  # ← BARU
        )
    except httpx.TimeoutException:
        raise ProviderTimeoutError(...)
    except httpx.ConnectError:
        raise ProviderConnectionError(...)

    if response.status_code != 200:
        if key_used and response.status_code in (401, 429):
            self._key_manager.report_failure(key_used)
        raise ProviderAPIError(...)

    if key_used:
        self._key_manager.report_success(key_used)

    # ... (response parsing tetap sama) ...
```

---

## 6. Output yang Diharapkan

### Tanpa key (model lokal) — behavior TIDAK BERUBAH:
```
POST /api/generate HTTP/1.1
Content-Type: application/json

{"model": "gemma4:e2b", "prompt": "Hello", "stream": false}
```

### Dengan key (model cloud):
```
POST /api/generate HTTP/1.1
Authorization: Bearer 750d793c...uii3
Content-Type: application/json

{"model": "glm-5.1:cloud", "prompt": "Hello", "stream": false}
```

---

## 7. Dependencies

- **Task 1** — `AllKeysExhaustedError` di exceptions.py
- **Task 2** — `KeyManager` class di key_manager.py

---

## 8. Acceptance Criteria

- [ ] `OllamaProvider(base_url, timeout)` tanpa key_manager → behavior 100% sama (zero-regression)
- [ ] `OllamaProvider(base_url, timeout, key_manager=km)` → header `Authorization: Bearer` terkirim
- [ ] `_get_auth_headers()` return `({}, None)` jika tidak ada key
- [ ] `_get_auth_headers()` return `({"Authorization": "Bearer ..."}, key)` jika ada key
- [ ] HTTP 429 → `report_failure(key)` dipanggil
- [ ] HTTP 200 → `report_success(key)` dipanggil
- [ ] Method `generate()`, `stream()`, `embedding()` semua mengirim header

---

## 9. Estimasi

**Medium** — Modifikasi 3 method + helper baru, tapi polanya repetitif.
