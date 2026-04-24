# Schema & Model Registry — beta0.1.2

> **Versi**: beta0.1.2  
> **Modul**: Pydantic Schemas, Model Registry, Response Normalization  
> **Status**: 📋 Planned  
> **Dependency**: beta0.1.1 (Foundation Core)  
> **Referensi Blueprint**: `03-service-layer.md`, `05-schemas.md`

---

## 1. Latar Belakang

Setelah fondasi project berdiri di beta0.1.1, langkah berikutnya adalah mendefinisikan **kontrak data** — bagaimana request masuk dan response keluar. Tanpa Pydantic schemas dan Model Registry, endpoint tidak bisa memvalidasi input, dan provider tidak punya acuan capability model.

Modul ini membangun **data layer** yang menjadi jembatan antara API Layer dan Service Layer.

### Masalah yang Diselesaikan

- Belum ada validasi input request → data bisa masuk dalam format apapun
- Belum ada format response standar → setiap provider bisa return format berbeda
- Belum ada catalog model → tidak tahu model mana yang support image atau embedding
- Capability model di-hardcode → sulit di-maintain saat model bertambah

### Kaitan dengan Sistem

- Schemas digunakan oleh **semua endpoint** (generate, stream, models, embedding)
- Model Registry digunakan oleh **GeneratorService** untuk validasi capability
- Response schemas memastikan **normalisasi output** dari semua provider
- Menjadi prasyarat untuk beta0.1.3 (Provider Abstraction)

---

## 2. Tujuan

| # | Outcome | Measurable |
|---|---|---|
| 1 | Semua request schema terdefinisi | `GenerateRequest`, `StreamRequest`, `EmbeddingRequest` valid |
| 2 | Semua response schema terdefinisi | `GenerateResponse`, `EmbeddingResponse`, `ModelInfo` valid |
| 3 | Model Registry berfungsi | Bisa register, lookup, dan list model |
| 4 | Default models terdaftar | 6 model (3 Ollama + 3 Gemini) registered saat startup |
| 5 | Endpoint GET /models tersedia | Return daftar model beserta capability |

---

## 3. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/schemas/common.py` (ProviderEnum, shared types)
- Implementasi `app/schemas/requests.py` (semua request models)
- Implementasi `app/schemas/responses.py` (semua response models)
- Implementasi `app/services/model_registry.py` (ModelRegistry class)
- Implementasi `GET /api/v1/models` endpoint
- Implementasi `app/api/dependencies.py` (dependency injection setup)
- Implementasi `app/api/router.py` (central router)

### ❌ Yang Tidak Dikerjakan

- Provider implementations → beta0.1.3
- GeneratorService → beta0.1.3 (butuh provider dulu)
- Endpoint /generate, /stream, /embedding → beta0.1.3+
- Auto-discovery model dari Ollama API → future version

---

## 4. Breakdown Task

### Task 1: Common Types

- [ ] Implementasi `app/schemas/common.py`
  - `ProviderEnum` — enum string: `"ollama"`, `"gemini"`

### Task 2: Request Schemas

- [ ] Implementasi `app/schemas/requests.py`
  - `GenerateRequest`:
    - `provider`: ProviderEnum (required)
    - `model`: str (required)
    - `input`: str (required, min_length=1)
    - `images`: Optional[list[str]]
    - `stream`: bool (default=False)
  - `StreamRequest`:
    - `provider`, `model`, `input`, `images` (sama seperti GenerateRequest tanpa stream flag)
  - `EmbeddingRequest`:
    - `provider`, `model`, `input`

### Task 3: Response Schemas

- [ ] Implementasi `app/schemas/responses.py`
  - `UsageInfo`: prompt_tokens, completion_tokens, total_tokens (semua optional int)
  - `GenerateResponse`: output, provider, model, usage, metadata
  - `ModelInfo`: name, provider, supports_text, supports_image, supports_embedding
  - `EmbeddingResponse`: embedding (list[float]), provider, model
  - `ErrorResponse`: error, code, detail

### Task 4: Model Registry

- [ ] Implementasi `app/services/model_registry.py`
  - Dataclass `ModelCapability`:
    - name, provider, supports_text, supports_image, supports_embedding
  - Class `ModelRegistry`:
    - `register(model)` — tambah model ke catalog
    - `get_model(provider, name)` — lookup, raise ModelNotFoundError jika tidak ada
    - `list_models(provider=None)` — list semua, optional filter by provider
    - `register_defaults()` — register 6 default models:
      - Ollama: llama3.2, llama3.2-vision, nomic-embed-text
      - Gemini: gemini-2.0-flash, gemini-2.5-flash-preview-04-17, text-embedding-004

### Task 5: Dependency Injection Setup

- [ ] Implementasi `app/api/dependencies.py`
  - Global variable `_model_registry`
  - `get_model_registry()` — FastAPI Depends function
  - `initialize_services()` — dipanggil dari startup event
  - Untuk saat ini: hanya init registry (provider & generator service ditambah di beta0.1.3)

### Task 6: Models Endpoint

- [ ] Implementasi `app/api/endpoints/models.py`
  - `GET /api/v1/models` — return list[ModelInfo]
  - Query param optional: `provider` (filter by provider)
- [ ] Implementasi `app/api/router.py`
  - Include models router

### Task 7: Update main.py

- [ ] Update `app/main.py` startup event:
  - Call `initialize_services(settings)`
  - Include api_router di app
  - Log jumlah model yang terdaftar

---

## 5. Design Teknis

### File Baru

| File | Layer | Fungsi |
|---|---|---|
| `app/schemas/__init__.py` | Schemas | Package init |
| `app/schemas/common.py` | Schemas | ProviderEnum |
| `app/schemas/requests.py` | Schemas | Request models |
| `app/schemas/responses.py` | Schemas | Response models |
| `app/services/__init__.py` | Services | Package init |
| `app/services/model_registry.py` | Services | ModelRegistry |
| `app/api/__init__.py` | API | Package init |
| `app/api/dependencies.py` | API | DI functions |
| `app/api/router.py` | API | Central router |
| `app/api/endpoints/__init__.py` | API | Package init |
| `app/api/endpoints/models.py` | API | GET /models endpoint |

### File yang Dimodifikasi

| File | Perubahan |
|---|---|
| `app/main.py` | Tambah router, startup init registry |

### Flow: GET /models

```
Client → GET /api/v1/models?provider=ollama
  → models.py endpoint
    → registry.list_models(provider="ollama")
    → Return filtered list[ModelInfo]
  → JSON Response: [{ name, provider, supports_* }]
```

### Flow: Startup (Updated)

```
1. [beta0.1.1] FastAPI starts, config loads, logging setup
2. [beta0.1.2] initialize_services() called:
   - ModelRegistry created
   - register_defaults() → 6 models registered
   - Log: "Registered 6 models"
3. Router included → /api/v1/models available
```

---

## 6. Dampak ke Sistem

### Bagian yang Berubah

- `app/main.py` — tambah router dan registry init
- Folder `app/schemas/`, `app/services/`, `app/api/` terisi implementasi

### Risiko

| Risiko | Mitigasi |
|---|---|
| Schema field salah nama | Validasi via Pydantic → error jelas saat import |
| Registry key collision | Format key `"{provider}:{model}"` mencegah collision |
| Default models outdated | Mudah diupdate di `register_defaults()` |

### Dependency

| Depends On | Depended By |
|---|---|
| beta0.1.1 (config, exceptions) | beta0.1.3 (provider needs registry) |
| — | Semua endpoint yang akan dibuat |

---

## 7. Definition of Done

- [ ] Semua schema bisa di-import tanpa error
- [ ] `GenerateRequest(provider="ollama", model="llama3.2", input="hi")` valid
- [ ] `GenerateRequest(provider="invalid", ...)` menghasilkan validation error
- [ ] `ModelRegistry` bisa register dan lookup model
- [ ] `registry.get_model("ollama", "nonexistent")` raise `ModelNotFoundError`
- [ ] `GET /api/v1/models` return JSON array dengan 6 default models
- [ ] `GET /api/v1/models?provider=gemini` return hanya 3 Gemini models
- [ ] Swagger UI menampilkan schema dan endpoint dengan benar

---

## Referensi Blueprint

- [03-service-layer.md](../bluprint/03-service-layer.md) — ModelRegistry design
- [05-schemas.md](../bluprint/05-schemas.md) — Pydantic models
- [04-api-layer.md](../bluprint/04-api-layer.md) — GET /models spec
