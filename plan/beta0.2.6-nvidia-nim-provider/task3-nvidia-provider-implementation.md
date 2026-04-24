# Task 3 — NvidiaProvider Implementation

## 1. Judul Task
Implementasi `NvidiaProvider` class dengan generate, stream, dan embedding methods

## 2. Deskripsi
Membuat class `NvidiaProvider` yang mengimplementasikan seluruh `BaseProvider` interface. Provider ini berkomunikasi dengan NVIDIA NIM API menggunakan OpenAI-compatible REST format via `httpx.AsyncClient`.

## 3. Tujuan Teknis
- `NvidiaProvider` inherit dari `BaseProvider`
- Method `generate()` — POST `/chat/completions`, normalize ke format gateway
- Method `stream()` — POST `/chat/completions` (stream=true), yield SSE tokens
- Method `embedding()` — POST `/embeddings` dengan `input_type: "query"`
- Error handling: `ProviderAPIError`, `ProviderTimeoutError`, `ProviderConnectionError`

## 4. Scope

### Termasuk
- `app/providers/nvidia.py` — full NvidiaProvider implementation
  - `__init__()` — httpx client setup with Bearer auth
  - `name` property → `"nvidia"`
  - `generate()` — convert prompt to chat format, extract response
  - `stream()` — parse SSE lines, yield delta.content tokens
  - `embedding()` — send with `input_type`, extract `data[0].embedding`
  - `supports_image()` → `False` (no vision support yet)
  - `close()` — cleanup httpx client

### Tidak Termasuk
- Factory registration (Task 4)
- Model registry defaults (Task 4)
- Health checker probe (Task 4)
- Unit tests (Task 5)

## 5. Langkah Implementasi

### Step 1: Buat `app/providers/nvidia.py`

```python
class NvidiaProvider(BaseProvider):
    def __init__(self, api_key: str, base_url: str, timeout: int = 120):
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout),
        )
```

### Step 2: Implement `generate()`
Key mapping dari NVIDIA response ke gateway format:
- `choices[0].message.content` → `output`
- `usage.prompt_tokens` → `usage.prompt_tokens`
- `usage.completion_tokens` → `usage.completion_tokens`
- `id` → `metadata.id`
- `choices[0].finish_reason` → `metadata.finish_reason`

Prompt dikirim sebagai single `user` message dalam format OpenAI:
```python
messages = [{"role": "user", "content": prompt}]
payload = {"model": model, "messages": messages, "max_tokens": 4096}
```

### Step 3: Implement `stream()`
NVIDIA streaming menggunakan SSE (Server-Sent Events):
- Setiap line diawali `data: `
- Content ada di `choices[0].delta.content`
- Stream diakhiri dengan `data: [DONE]`
- Skip lines tanpa `data: ` prefix
- Skip malformed JSON lines

### Step 4: Implement `embedding()`
Key NVIDIA-specific quirk: **`input_type` parameter wajib** untuk asymmetric models.
```python
payload = {
    "model": model,
    "input": input_text,
    "input_type": "query",  # ← NVIDIA-specific, tidak ada di OpenAI standard
}
```
Response: extract `data[0].embedding` (list[float])

### Step 5: Error handling pattern
Sama dengan OllamaProvider:
- `httpx.TimeoutException` → `ProviderTimeoutError`
- `httpx.ConnectError` → `ProviderConnectionError`
- Non-200 status → `ProviderAPIError`

## 6. Output yang Diharapkan

```python
provider = NvidiaProvider(api_key="nvapi-...", base_url="https://integrate.api.nvidia.com/v1")
assert provider.name == "nvidia"
assert provider.supports_image("any") is False

result = await provider.generate(model="meta/llama-3.3-70b-instruct", prompt="Hello")
assert result["provider"] == "nvidia"
assert result["output"] != ""
assert result["usage"]["total_tokens"] > 0
```

## 7. Dependencies
- Task 2 (config dan base imports)
- Exploratory findings dari Task 1 (response format)

## 8. Acceptance Criteria
- [x] `NvidiaProvider` inherits `BaseProvider` dan implements semua abstract methods
- [x] `generate()` — POST ke `/chat/completions`, return normalized dict
- [x] `stream()` — SSE streaming, yield individual tokens, handle `[DONE]`
- [x] `embedding()` — POST ke `/embeddings` dengan `input_type: "query"`
- [x] Empty embedding → `ProviderAPIError`
- [x] Timeout → `ProviderTimeoutError`
- [x] Connection error → `ProviderConnectionError`
- [x] Non-200 status → `ProviderAPIError` with status detail
- [x] `supports_image()` returns `False`
- [x] `close()` calls `_client.aclose()`

## 9. Estimasi
Medium (~1 jam)
