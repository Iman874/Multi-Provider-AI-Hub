# Provider Abstraction & Ollama — beta0.1.3

> **Versi**: beta0.1.3  
> **Modul**: BaseProvider Abstraction, OllamaProvider, GeneratorService, POST /generate  
> **Status**: 📋 Planned  
> **Dependency**: beta0.1.2 (Schema & Model Registry)  
> **Referensi Blueprint**: `02-provider-layer.md`, `03-service-layer.md`, `04-api-layer.md`

---

## 1. Latar Belakang

Setelah data layer (schemas + registry) siap di beta0.1.2, saatnya membangun **inti dari AI gateway** — provider abstraction layer dan provider pertama yang berfungsi.

Dipilih **Ollama sebagai provider pertama** karena:
- Berjalan di localhost → tidak butuh API key → test lebih cepat
- Latency lebih rendah → development cycle cepat
- Membuktikan abstraction pattern bekerja sebelum menambah Gemini

Pada versi ini juga dibangun **GeneratorService** yang menjadi orchestrator utama, dan **endpoint POST /generate** sebagai endpoint pertama yang benar-benar menghasilkan AI output.

### Masalah yang Diselesaikan

- Belum ada koneksi ke AI provider manapun
- Belum ada abstraction layer → kalau langsung hardcode, sulit tambah provider
- Belum ada service layer → endpoint akan berisi logic yang seharusnya terpisah
- Belum ada endpoint yang benar-benar generate output AI

### Kaitan dengan Sistem

- `BaseProvider` menjadi kontrak untuk **semua provider** (Gemini, future providers)
- `OllamaProvider` adalah implementasi pertama yang membuktikan pattern bekerja
- `GeneratorService` menjadi **satu-satunya orchestrator** — endpoint TIDAK BOLEH langsung call provider
- `POST /generate` adalah endpoint pertama yang menghasilkan output AI nyata

---

## 2. Tujuan

| # | Outcome | Measurable |
|---|---|---|
| 1 | Abstract BaseProvider terdefinisi | 4 abstract methods: generate, stream, embedding, supports_image |
| 2 | OllamaProvider berfungsi | Generate text dari Ollama lokal berhasil |
| 3 | GeneratorService berfungsi | Route request ke provider + validasi capability |
| 4 | POST /generate endpoint live | Kirim prompt, terima AI-generated text |
| 5 | Error handling terintegrasi | Provider not found → 404, connection error → 502 |

---

## 3. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/providers/base.py` (abstract BaseProvider)
- Implementasi `app/providers/ollama.py` (OllamaProvider — text generate only)
- Implementasi `app/providers/__init__.py` (provider factory)
- Implementasi `app/services/generator.py` (GeneratorService — generate method)
- Implementasi `app/api/endpoints/generate.py` (POST /generate)
- Update `app/api/dependencies.py` (register provider + generator service)
- Update `app/main.py` (startup: init providers)

### ❌ Yang Tidak Dikerjakan

- GeminiProvider → beta0.1.4
- Streaming (POST /stream) → beta0.1.5
- Embedding (POST /embedding) → beta0.1.6
- Multimodal / image support → beta0.1.5+
- OllamaProvider.stream() dan embedding() → stub only, implementasi di versi terkait

---

## 4. Breakdown Task

### Task 1: Abstract Base Provider

- [ ] Implementasi `app/providers/base.py`
  - Abstract class `BaseProvider(ABC)`
  - Property abstract: `name` → str
  - Method abstract: `generate(model, prompt, images)` → dict
  - Method abstract: `stream(model, prompt, images)` → AsyncGenerator
  - Method abstract: `embedding(model, input_text)` → list[float]
  - Method abstract: `supports_image(model)` → bool
  - Method: `close()` → cleanup (default no-op)

### Task 2: OllamaProvider — Generate

- [ ] Implementasi `app/providers/ollama.py`
  - Constructor: `__init__(base_url, timeout)` → setup `httpx.AsyncClient`
  - Property `name` → `"ollama"`
  - Method `generate()`:
    - Build payload: `{ model, prompt, stream: false }`
    - POST ke `{base_url}/api/generate`
    - Parse response JSON
    - Normalize ke: `{ output, model, provider, usage, metadata }`
    - Handle errors: timeout → `ProviderTimeoutError`, connection → `ProviderConnectionError`
  - Method `stream()` → stub: `raise NotImplementedError` (beta0.1.5)
  - Method `embedding()` → stub: `raise NotImplementedError` (beta0.1.6)
  - Method `supports_image()` → return False (beta0.1.5)
  - Method `close()` → close httpx client

### Task 3: Provider Factory

- [ ] Implementasi `app/providers/__init__.py`
  - Function `create_provider(name, settings)` → BaseProvider
  - Match "ollama" → OllamaProvider
  - Match "gemini" → placeholder (log warning, skip)
  - Unknown → raise ValueError

### Task 4: Generator Service — Generate

- [ ] Implementasi `app/services/generator.py`
  - Class `GeneratorService`
  - Constructor: `__init__(providers: dict, registry: ModelRegistry)`
  - Private method `_get_provider(name)` → resolve atau raise `ProviderNotFoundError`
  - Method `generate(request: GenerateRequest)`:
    1. Resolve provider
    2. Lookup model di registry → raise `ModelNotFoundError` jika tidak ada
    3. Jika images ada → cek `supports_image` → raise `ModelCapabilityError` jika tidak support
    4. Call `provider.generate(model, prompt, images)`
    5. Wrap result dalam `GenerateResponse`
    6. Return

### Task 5: POST /generate Endpoint

- [ ] Implementasi `app/api/endpoints/generate.py`
  - Route: `POST /generate`
  - Accept: `GenerateRequest` (body)
  - Inject: `GeneratorService` via Depends
  - Call: `service.generate(request)`
  - Return: `GenerateResponse`
  - **Endpoint HANYA 3 baris logic — tidak ada business logic**

### Task 6: Update Dependencies & Startup

- [ ] Update `app/api/dependencies.py`:
  - Tambah `_generator_service` global
  - Tambah `get_generator_service()` Depends function
  - Update `initialize_services()`:
    - Create OllamaProvider (skip Gemini jika no API key)
    - Create GeneratorService(providers, registry)
- [ ] Update `app/api/router.py`:
  - Include generate router
- [ ] Update `app/main.py`:
  - Startup: test Ollama connectivity (log warning if unreachable)
  - Shutdown: close all provider HTTP clients

---

## 5. Design Teknis

### File Baru

| File | Layer | Fungsi |
|---|---|---|
| `app/providers/__init__.py` | Provider | Factory function |
| `app/providers/base.py` | Provider | Abstract contract |
| `app/providers/ollama.py` | Provider | Ollama integration |
| `app/services/generator.py` | Service | Orchestrator |
| `app/api/endpoints/generate.py` | API | POST /generate |

### File yang Dimodifikasi

| File | Perubahan |
|---|---|
| `app/api/dependencies.py` | Tambah generator service init |
| `app/api/router.py` | Include generate router |
| `app/main.py` | Startup init providers, shutdown cleanup |

### Flow: POST /generate (Text Only)

```
Client → POST /api/v1/generate
  Body: { provider: "ollama", model: "llama3.2", input: "Hello" }

→ generate.py endpoint
  → service.generate(request)
    → _get_provider("ollama") → OllamaProvider
    → registry.get_model("ollama", "llama3.2") → ModelCapability
    → provider.generate("llama3.2", "Hello", None)
      → POST http://localhost:11434/api/generate
        Body: { model: "llama3.2", prompt: "Hello", stream: false }
      ← { response: "Hi there!...", ... }
    ← { output: "Hi there!...", model: "llama3.2", provider: "ollama", usage: {...} }
  ← GenerateResponse(...)

→ JSON Response 200:
  { output: "Hi there!...", provider: "ollama", model: "llama3.2", usage: {...} }
```

### Flow: Error — Provider Not Found

```
Client → POST /api/v1/generate
  Body: { provider: "openai", model: "gpt-4", input: "Hello" }

→ service.generate(request)
  → _get_provider("openai") → raise ProviderNotFoundError
→ gateway_error_handler catches
→ JSON Response 404:
  { error: "Provider 'openai' not found or disabled", code: "PROVIDER_NOT_FOUND" }
```

---

## 6. Dampak ke Sistem

### Bagian yang Berubah

- `app/api/dependencies.py` — extended dengan generator service
- `app/api/router.py` — tambah generate route
- `app/main.py` — startup/shutdown diperkaya
- Folder `app/providers/` dan `app/services/` terisi implementasi

### Risiko

| Risiko | Mitigasi |
|---|---|
| Ollama tidak jalan di localhost | Startup log warning, endpoint return 502 |
| Response format Ollama berubah | Parse defensif + ProviderAPIError |
| Timeout saat generate long text | Configurable timeout di settings |

### Dependency

| Depends On | Depended By |
|---|---|
| beta0.1.1 (config, exceptions) | beta0.1.4 (Gemini provider) |
| beta0.1.2 (schemas, registry) | beta0.1.5 (streaming) |
| — | beta0.1.6 (embedding) |

---

## 7. Definition of Done

- [ ] `BaseProvider` bisa di-import dan di-extend tanpa error
- [ ] `OllamaProvider` berhasil generate text dari Ollama lokal
- [ ] `GeneratorService.generate()` return `GenerateResponse` yang valid
- [ ] `POST /api/v1/generate` dengan provider "ollama" return AI-generated text
- [ ] Request ke provider yang tidak ada → 404 JSON error
- [ ] Request ke model yang tidak terdaftar → 404 JSON error
- [ ] Ollama timeout → 504 JSON error
- [ ] Ollama tidak reachable → 502 JSON error
- [ ] Swagger UI menampilkan POST /generate dengan schema yang benar
- [ ] Response format sesuai `GenerateResponse` schema

---

## Referensi Blueprint

- [02-provider-layer.md](../bluprint/02-provider-layer.md) — BaseProvider & Ollama design
- [03-service-layer.md](../bluprint/03-service-layer.md) — GeneratorService design
- [04-api-layer.md](../bluprint/04-api-layer.md) — POST /generate spec
