# Task 1 — Exploratory API Testing

## 1. Judul Task
Buat script exploratory untuk test NVIDIA NIM API secara manual

## 2. Deskripsi
Sebelum implementasi provider, perlu memahami format request/response aktual dari NVIDIA NIM API. Script ini akan test 4 endpoint utama: list models, chat completion, streaming, dan embedding.

## 3. Tujuan Teknis
- Verifikasi API key (`nvapi-...`) bisa authenticate
- Mapping format response aktual vs dokumentasi
- Identifikasi quirk/perbedaan dari standar OpenAI (contoh: `input_type` required untuk embedding)
- Catat model ID yang valid dan tersedia

## 4. Scope

### Termasuk
- `scripts/explore_nvidia_api.py` — script test manual dengan 4 test case
- Test 1: `GET /v1/models` — list available models
- Test 2: `POST /v1/chat/completions` — non-streaming generate
- Test 3: `POST /v1/chat/completions` (stream=true) — SSE streaming
- Test 4: `POST /v1/embeddings` — vector embedding

### Tidak Termasuk
- Config system (Task 2)
- NvidiaProvider class (Task 3)
- Integration ke gateway (Task 4)
- Unit tests (Task 5)

## 5. Langkah Implementasi

### Step 1: Buat file `scripts/explore_nvidia_api.py`

Script standalone yang menggunakan `httpx` langsung (tanpa framework):

```python
import httpx
import json
import os

BASE_URL = "https://integrate.api.nvidia.com/v1"
API_KEY = os.getenv("NVIDIA_API_KEY", "")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}
```

### Step 2: Test list models
```python
resp = httpx.get(f"{BASE_URL}/models", headers=HEADERS, timeout=30)
# Expected: 200 OK, JSON with "data" array of model objects
```

### Step 3: Test chat completion (non-streaming)
```python
resp = httpx.post(f"{BASE_URL}/chat/completions", headers=HEADERS, json={
    "model": "meta/llama-3.3-70b-instruct",
    "messages": [{"role": "user", "content": "Say hello in 1 sentence."}],
    "max_tokens": 50,
})
# Expected: OpenAI-compatible response with choices[0].message.content
```

### Step 4: Test streaming
```python
with httpx.stream("POST", f"{BASE_URL}/chat/completions", headers=HEADERS, json={
    "model": "meta/llama-3.3-70b-instruct",
    "messages": [{"role": "user", "content": "Count from 1 to 5."}],
    "stream": True,
}) as resp:
    for line in resp.iter_lines():
        # Expected: "data: {json}" lines, ending with "data: [DONE]"
```

### Step 5: Test embedding
```python
resp = httpx.post(f"{BASE_URL}/embeddings", headers=HEADERS, json={
    "model": "nvidia/nv-embedqa-e5-v5",
    "input": "Test text",
    "input_type": "query",  # ← NVIDIA-specific! Required for asymmetric models
})
# Expected: OpenAI-compatible response with data[0].embedding
```

### Step 6: Jalankan dan catat findings

```powershell
$env:NVIDIA_API_KEY='nvapi-...'; .\venv\Scripts\python scripts\explore_nvidia_api.py
```

## 6. Output yang Diharapkan

Findings dari exploratory test:

| Test | Status | Notes |
|------|--------|-------|
| List models | ✅ 200 | 133 models available |
| Chat completion | ✅ 200 | OpenAI-compatible format confirmed |
| Streaming | ✅ 200 | SSE format `data: {json}` + `data: [DONE]` |
| Embedding | ✅ 200 | **Requires `input_type: "query"`** (NVIDIA quirk) |

Key finding: Embedding endpoint memerlukan parameter `input_type` (`"query"` atau `"passage"`) — ini berbeda dari standard OpenAI.

## 7. Dependencies
- Tidak ada (task pertama)
- Hanya butuh `httpx` (sudah ada di requirements)

## 8. Acceptance Criteria
- [x] Script `scripts/explore_nvidia_api.py` berjalan tanpa error
- [x] API key `nvapi-...` berhasil authenticate
- [x] Format response generate terverifikasi (OpenAI-compatible)
- [x] Format response streaming terverifikasi (SSE)
- [x] Format response embedding terverifikasi (perlu `input_type`)
- [x] Model ID yang valid tercatat untuk registry

## 9. Estimasi
Low (~30 menit)
