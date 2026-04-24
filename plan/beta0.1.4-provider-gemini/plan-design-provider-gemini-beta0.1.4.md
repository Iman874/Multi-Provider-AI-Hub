# Gemini Provider — beta0.1.4

> **Versi**: beta0.1.4  
> **Modul**: GeminiProvider (Text Generation)  
> **Status**: 📋 Planned  
> **Dependency**: beta0.1.3 (Provider Abstraction & Ollama)  
> **Referensi Blueprint**: `02-provider-layer.md`, `06-config-and-env.md`

---

## 1. Latar Belakang

Di beta0.1.3, kita sudah membuktikan bahwa provider abstraction pattern bekerja dengan OllamaProvider. Sekarang saatnya menambahkan **provider kedua — Google Gemini** — untuk memvalidasi bahwa arsitektur benar-benar scalable.

Jika GeminiProvider bisa ditambahkan **tanpa mengubah** endpoint, service, atau Ollama code — maka arsitektur kita terbukti solid.

### Masalah yang Diselesaikan

- Hanya ada 1 provider → belum terbukti arsitektur multi-provider bekerja
- Belum ada opsi cloud LLM → hanya bisa pakai local model
- User belum bisa pilih antara lokal (Ollama) vs cloud (Gemini)

### Kaitan dengan Sistem

- Menggunakan `BaseProvider` yang sudah ada (beta0.1.3)
- Terintegrasi otomatis dengan `GeneratorService` tanpa modifikasi
- `ModelRegistry` sudah punya default Gemini models (beta0.1.2)
- Menambah case di `create_provider()` factory

---

## 2. Tujuan

| # | Outcome | Measurable |
|---|---|---|
| 1 | GeminiProvider implements BaseProvider | Semua abstract methods ter-implement |
| 2 | Text generation via Gemini berfungsi | POST /generate dengan provider="gemini" return text |
| 3 | Zero perubahan pada endpoint/service | Tidak ada edit di generate.py atau generator.py |
| 4 | Graceful degradation | Jika GEMINI_API_KEY kosong → provider disabled, bukan crash |
| 5 | Error handling konsisten | Timeout/API error dari Gemini → standard error response |

---

## 3. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/providers/gemini.py` (GeminiProvider — text generate)
- Update `app/providers/__init__.py` (factory: tambah gemini case)
- Update `app/api/dependencies.py` (conditional init Gemini)
- Startup validation: cek API key, log status

### ❌ Yang Tidak Dikerjakan

- Gemini streaming → beta0.1.5
- Gemini embedding → beta0.1.6
- Gemini multimodal (image) → beta0.1.7
- Method stream() dan embedding() → stub only

---

## 4. Breakdown Task

### Task 1: GeminiProvider Implementation

- [ ] Implementasi `app/providers/gemini.py`
  - Constructor: `__init__(api_key, timeout)`
    - Init `google.genai.Client(api_key=api_key)`
  - Property `name` → `"gemini"`
  - Method `generate(model, prompt, images=None)`:
    - Build contents: `[prompt]` (text only untuk versi ini)
    - Call `client.models.generate_content(model=model, contents=contents)`
    - Parse `response.text`
    - Extract usage info jika tersedia
    - Normalize ke standard dict: `{ output, model, provider, usage, metadata }`
    - Wrap errors: API error → `ProviderAPIError`, timeout → `ProviderTimeoutError`
  - Method `stream()` → stub: raise `NotImplementedError`
  - Method `embedding()` → stub: raise `NotImplementedError`
  - Method `supports_image()` → return False (enabled di beta0.1.7)
  - Method `close()` → no-op (SDK manages connection)

### Task 2: Update Provider Factory

- [ ] Update `app/providers/__init__.py`
  - Tambah case `"gemini"` di `create_provider()`
  - Import GeminiProvider

### Task 3: Conditional Provider Initialization

- [ ] Update `app/api/dependencies.py`
  - `initialize_services()`:
    - Cek `settings.GEMINI_API_KEY`
    - Jika kosong → log warning, JANGAN register Gemini provider
    - Jika ada → create GeminiProvider, tambah ke providers dict
  - Providers dict sekarang bisa berisi 1 atau 2 provider

### Task 4: Startup Validation

- [ ] Update `app/main.py` startup event:
  - Log provider yang aktif: "Active providers: ollama, gemini" atau "Active providers: ollama"
  - Log jumlah model per provider

---

## 5. Design Teknis

### File Baru

| File | Layer | Fungsi |
|---|---|---|
| `app/providers/gemini.py` | Provider | Google Gemini integration |

### File yang Dimodifikasi

| File | Perubahan |
|---|---|
| `app/providers/__init__.py` | Tambah gemini case di factory |
| `app/api/dependencies.py` | Conditional Gemini init |
| `app/main.py` | Log active providers |

### Flow: POST /generate (Gemini)

```
Client → POST /api/v1/generate
  Body: { provider: "gemini", model: "gemini-2.0-flash", input: "Hello" }

→ service.generate(request)
  → _get_provider("gemini") → GeminiProvider
  → registry.get_model("gemini", "gemini-2.0-flash") → OK
  → provider.generate("gemini-2.0-flash", "Hello", None)
    → client.models.generate_content(model="gemini-2.0-flash", contents=["Hello"])
    ← response.text = "Hello! How can I help you?"
  ← { output: "Hello! How can I help you?", provider: "gemini", ... }

→ JSON Response 200
```

### Validasi: Zero-Change Proof

File yang **TIDAK** boleh berubah di versi ini:
- `app/api/endpoints/generate.py` ← endpoint tetap sama
- `app/services/generator.py` ← service tetap sama
- `app/providers/ollama.py` ← Ollama tidak terpengaruh
- `app/schemas/*` ← schemas tidak berubah

---

## 6. Dampak ke Sistem

### Bagian yang Berubah

- Provider layer: 1 file baru, 1 file update
- Dependencies: conditional init logic
- Startup: enhanced logging

### Risiko

| Risiko | Mitigasi |
|---|---|
| API key invalid | google-genai SDK throw error → wrap jadi ProviderAPIError |
| Rate limiting Gemini | Catch 429 error → ProviderAPIError dengan detail |
| SDK version mismatch | Pin `google-genai>=1.0` di requirements |

### Dependency

| Depends On | Depended By |
|---|---|
| beta0.1.3 (BaseProvider, factory) | beta0.1.5 (Gemini streaming) |
| beta0.1.2 (Gemini models in registry) | beta0.1.6 (Gemini embedding) |

---

## 7. Definition of Done

- [ ] `GeminiProvider` implements semua method dari `BaseProvider`
- [ ] `POST /generate` dengan `provider="gemini"` return AI text
- [ ] Tanpa API key → Gemini disabled, Ollama tetap jalan
- [ ] Tidak ada perubahan di `generate.py`, `generator.py`, atau `ollama.py`
- [ ] Gemini API error → standard JSON error (502)
- [ ] Gemini timeout → standard JSON error (504)
- [ ] Swagger UI menunjukkan provider "gemini" sebagai opsi valid

---

## Referensi Blueprint

- [02-provider-layer.md](../bluprint/02-provider-layer.md) — GeminiProvider design
- [06-config-and-env.md](../bluprint/06-config-and-env.md) — GEMINI_API_KEY config
