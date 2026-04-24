# Streaming Adapter — beta0.1.5

> **Versi**: beta0.1.5  
> **Modul**: SSE Streaming untuk Ollama & Gemini, POST /stream Endpoint  
> **Status**: 📋 Planned  
> **Dependency**: beta0.1.4 (Gemini Provider)  
> **Referensi Blueprint**: `02-provider-layer.md`, `04-api-layer.md`

---

## 1. Latar Belakang

Text generation sudah berfungsi untuk kedua provider (beta0.1.3 & 0.1.4), tapi responsnya **menunggu sampai selesai** baru dikirim. Untuk UX yang baik di SaaS — terutama chat interface — **streaming token per chunk** sangat penting.

Tantangan utama: Ollama dan Gemini punya mekanisme streaming yang **sangat berbeda**:
- **Ollama**: NDJSON (newline-delimited JSON) via HTTP stream
- **Gemini**: SDK method `generate_content_stream()` yang return iterable

Modul ini membangun **streaming adapter** yang menyatukan keduanya ke format SSE (Server-Sent Events) yang uniform.

### Masalah yang Diselesaikan

- User harus menunggu seluruh response selesai → UX lambat
- Dua provider punya streaming format berbeda → perlu normalisasi
- Belum ada SSE endpoint → client tidak bisa consume stream

### Kaitan dengan Sistem

- Menggunakan `BaseProvider.stream()` yang sudah di-define (tapi masih stub)
- Menambah method `stream()` di `GeneratorService`
- Menambah endpoint `POST /stream` di API layer
- Depends on `sse-starlette` package (sudah di requirements)

---

## 2. Tujuan

| # | Outcome | Measurable |
|---|---|---|
| 1 | Ollama stream berfungsi | Token dikirim satu per satu via SSE |
| 2 | Gemini stream berfungsi | Token dikirim satu per satu via SSE |
| 3 | Format SSE seragam | Kedua provider output format `data: {"token": "..."}` identik |
| 4 | POST /stream endpoint live | Client bisa consume stream via curl / EventSource |
| 5 | Final event marker | Stream diakhiri dengan `data: [DONE]` |

---

## 3. Scope

### ✅ Yang Dikerjakan

- Implementasi `OllamaProvider.stream()` — NDJSON parsing
- Implementasi `GeminiProvider.stream()` — SDK stream iteration
- Implementasi `GeneratorService.stream()` — routing + validation
- Implementasi `app/api/endpoints/stream.py` — POST /stream (SSE)
- Update router untuk include stream endpoint

### ❌ Yang Tidak Dikerjakan

- Streaming dengan image input → beta0.1.7
- WebSocket alternative → future version
- Client-side streaming SDK → out of scope
- Retry/reconnect logic → future version

---

## 4. Breakdown Task

### Task 1: OllamaProvider.stream()

- [ ] Implementasi di `app/providers/ollama.py`
  - Build payload: `{ model, prompt, stream: true }`
  - POST ke `/api/generate` dengan `stream=True` di httpx
  - Iterate response lines (NDJSON):
    - Parse setiap line sebagai JSON
    - Extract field `response` → yield sebagai token string
    - Jika `done: true` → stop iteration
  - Error handling: timeout, connection error

### Task 2: GeminiProvider.stream()

- [ ] Implementasi di `app/providers/gemini.py`
  - Build contents: `[prompt]` (text only)
  - Call `client.models.generate_content_stream(model=model, contents=contents)`
  - Iterate chunks:
    - Extract `chunk.text` → yield sebagai token string
    - Skip empty chunks
  - Error handling: API error, timeout

### Task 3: GeneratorService.stream()

- [ ] Implementasi di `app/services/generator.py`
  - Method `stream(request: StreamRequest) -> AsyncGenerator[str, None]`
  - Flow:
    1. Resolve provider via `_get_provider()`
    2. Validate model exists di registry
    3. Jika images ada → validate supports_image (prep untuk beta0.1.7)
    4. `async for token in provider.stream(...)`: yield token

### Task 4: POST /stream Endpoint

- [ ] Implementasi `app/api/endpoints/stream.py`
  - Route: `POST /stream`
  - Accept: `StreamRequest` body
  - Inject: `GeneratorService` via Depends
  - Response: `EventSourceResponse` dari `sse-starlette`
  - Event generator:
    ```
    async for token in service.stream(request):
        yield {"data": json.dumps({"token": token})}
    yield {"data": "[DONE]"}
    ```
  - Content-Type: `text/event-stream`

### Task 5: Router Update

- [ ] Update `app/api/router.py`
  - Include stream router dengan tag "Streaming"

---

## 5. Design Teknis

### File Baru

| File | Layer | Fungsi |
|---|---|---|
| `app/api/endpoints/stream.py` | API | POST /stream endpoint |

### File yang Dimodifikasi

| File | Perubahan |
|---|---|
| `app/providers/ollama.py` | Implement `stream()` (replace stub) |
| `app/providers/gemini.py` | Implement `stream()` (replace stub) |
| `app/services/generator.py` | Add `stream()` method |
| `app/api/router.py` | Include stream router |

### SSE Output Format (Standard)

```
data: {"token": "Quantum"}

data: {"token": " computing"}

data: {"token": " uses"}

data: {"token": " quantum"}

data: {"token": " bits"}

data: [DONE]

```

Kedua provider HARUS menghasilkan format ini — normalisasi terjadi di provider layer.

### Flow: Ollama Stream

```
POST /api/generate (stream: true)
  ← Line: {"model":"llama3.2","response":"Quantum","done":false}
  ← Line: {"model":"llama3.2","response":" computing","done":false}
  ← Line: {"model":"llama3.2","response":"","done":true}

→ OllamaProvider.stream() yields: "Quantum", " computing"
→ Endpoint wraps: data: {"token": "Quantum"}, data: {"token": " computing"}, data: [DONE]
```

### Flow: Gemini Stream

```
generate_content_stream(model, contents)
  ← chunk.text = "Quantum"
  ← chunk.text = " computing uses"
  ← (iteration ends)

→ GeminiProvider.stream() yields: "Quantum", " computing uses"
→ Endpoint wraps: data: {"token": "..."}, ..., data: [DONE]
```

---

## 6. Dampak ke Sistem

### Bagian yang Berubah

- Kedua provider: stub `stream()` diganti implementasi real
- Service layer: method baru ditambahkan
- API layer: 1 endpoint baru

### Risiko

| Risiko | Mitigasi |
|---|---|
| Client disconnect mid-stream | httpx & sse-starlette handle cleanup otomatis |
| Ollama response bukan valid JSON | Try/except per line, skip malformed |
| Gemini stream timeout | Set reasonable timeout, catch exception |
| Empty chunks from Gemini | Filter `if chunk.text` sebelum yield |

### Dependency

| Depends On | Depended By |
|---|---|
| beta0.1.3 (OllamaProvider) | beta0.1.7 (streaming + images) |
| beta0.1.4 (GeminiProvider) | Future: WebSocket adapter |
| sse-starlette package | — |

---

## 7. Definition of Done

- [ ] `POST /stream` dengan Ollama → stream tokens via SSE
- [ ] `POST /stream` dengan Gemini → stream tokens via SSE
- [ ] Kedua provider output format SSE yang identik
- [ ] Stream diakhiri dengan `data: [DONE]`
- [ ] `curl -N -X POST /api/v1/stream ...` menampilkan token satu per satu
- [ ] Provider not found → proper error (bukan stream)
- [ ] Model not found → proper error (bukan stream)
- [ ] Client disconnect → no server crash
- [ ] Swagger UI menampilkan POST /stream endpoint

---

## Referensi Blueprint

- [02-provider-layer.md](../bluprint/02-provider-layer.md) — stream() method spec
- [04-api-layer.md](../bluprint/04-api-layer.md) — POST /stream endpoint spec
