# Coding Style — AI Generative Core

> Aturan ini berlaku untuk seluruh codebase `ai-local-api`.  
> Semua contributor dan AI agent WAJIB mengikuti aturan ini.

---

## 1. Python & Async

- **Python 3.12+** — gunakan fitur modern (`match/case`, `type | None`, dll).
- **Typing hints ketat** di semua function signatures:
  ```python
  async def generate(self, request: GenerateRequest) -> GenerateResponse:
  ```
- **Async-first**: semua I/O (HTTP, provider calls) HARUS `async def` + `await`.
- **Jangan gunakan `print()`** — gunakan `loguru.logger` untuk semua output.

---

## 2. Arsitektur 3-Layer

```
API Layer (endpoints) → Service Layer (business logic) → Provider Layer (AI integration)
```

### API Layer (`app/api/endpoints/`)
- Endpoint hanya **parse → call service → return**.
- **TIDAK BOLEH** ada business logic di endpoint.
- Inject dependency via FastAPI `Depends()`.
- Contoh benar:
  ```python
  @router.post("/generate")
  async def generate(
      request: GenerateRequest,
      service: GeneratorService = Depends(get_generator_service),
  ) -> GenerateResponse:
      return await service.generate(request)
  ```

### Service Layer (`app/services/`)
- Semua business logic ada di sini.
- `GeneratorService` adalah **satu-satunya orchestrator**.
- Endpoint **TIDAK BOLEH** langsung call provider.
- Validasi capability (image support, embedding support) di service layer.

### Provider Layer (`app/providers/`)
- Semua provider HARUS extend `BaseProvider` (ABC).
- Provider hanya tahu cara berkomunikasi dengan API masing-masing.
- Response HARUS di-normalize ke format standard (`dict` dengan keys: `output`, `model`, `provider`, `usage`, `metadata`).
- Menambah provider baru = **zero changes** di endpoint dan service.

---

## 3. Pydantic Models (V2)

- Selalu gunakan Pydantic `BaseModel` (V2) untuk semua data contracts.
- **Request schemas**: `app/schemas/requests.py`
- **Response schemas**: `app/schemas/responses.py`
- **Common types**: `app/schemas/common.py` (enums, shared types)
- Gunakan `Field()` dengan `description` untuk Swagger docs.
- Contoh:
  ```python
  class GenerateRequest(BaseModel):
      provider: ProviderEnum
      model: str = Field(..., description="Model identifier")
      input: str = Field(..., min_length=1)
      images: Optional[list[str]] = None
  ```

---

## 4. Configuration

- Gunakan `pydantic-settings` (`BaseSettings`) untuk environment config.
- Semua config di `app/config.py`, load dari `.env`.
- **JANGAN hardcode** URL, API key, atau timeout di kode.
- Access via singleton: `from app.config import settings`.

---

## 5. Error Handling

- Gunakan custom exception hierarchy dari `app/core/exceptions.py`:
  - `AIGatewayError` (base)
  - `ProviderNotFoundError`, `ModelNotFoundError`, `ModelCapabilityError`
  - `ProviderConnectionError`, `ProviderTimeoutError`, `ProviderAPIError`
- Setiap exception memiliki `code` (string) dan `message`.
- Global exception handler di `app/main.py` menangani semua `AIGatewayError` → JSON response.
- **JANGAN** catch-all `except Exception` di endpoint. Biarkan exception bubbling ke global handler.

---

## 6. Logging

- Gunakan `loguru` (bukan `logging` stdlib).
- Setup via `app/core/logging.py` → `setup_logging()`.
- Format: JSON (production) atau text (development).
- Pattern:
  ```python
  logger.info("Action: {detail}", detail=value)
  logger.debug("Generating: provider={provider}", provider=name)
  logger.error("Failed: {code}", code=exc.code)
  ```
- **JANGAN** log sensitive data (API keys, full prompts di production).

---

## 7. Dependency Injection

- Singleton services di `app/api/dependencies.py`.
- `initialize_services(settings)` dipanggil saat startup.
- Provides: `get_model_registry()`, `get_generator_service()`.
- Provider instances di-manage oleh dependency module, bukan endpoint.

---

## 8. Provider Pattern

- Factory function: `create_provider(name, settings)` di `app/providers/__init__.py`.
- Abstract contract: `BaseProvider` di `app/providers/base.py`.
- Setiap provider file: `app/providers/ollama.py`, `app/providers/gemini.py`.
- HTTP client: gunakan `httpx.AsyncClient` (bukan `requests`).
- Provider cleanup: `close()` dipanggil saat shutdown.

---

## 9. Model Registry

- Semua model HARUS terdaftar di `ModelRegistry` sebelum bisa dipakai.
- Default models di-register via `register_defaults()`.
- Capability flags: `supports_text`, `supports_image`, `supports_embedding`.
- Key format: `"{provider}:{model_name}"`.

---

## 10. File Structure

```
app/
├── api/
│   ├── dependencies.py      # DI: get_model_registry, get_generator_service
│   ├── router.py             # Central API router
│   └── endpoints/
│       ├── models.py         # GET /models
│       ├── generate.py       # POST /generate
│       ├── stream.py         # POST /stream
│       └── embedding.py      # POST /embedding
├── core/
│   ├── exceptions.py         # Custom exception hierarchy
│   ├── logging.py            # Loguru setup
│   └── middleware.py         # Request logging middleware
├── providers/
│   ├── __init__.py           # Provider factory
│   ├── base.py               # BaseProvider ABC
│   ├── ollama.py             # OllamaProvider
│   └── gemini.py             # GeminiProvider
├── schemas/
│   ├── common.py             # ProviderEnum, shared types
│   ├── requests.py           # GenerateRequest, StreamRequest, EmbeddingRequest
│   └── responses.py          # GenerateResponse, EmbeddingResponse, ModelInfo
├── services/
│   ├── generator.py          # GeneratorService (orchestrator)
│   └── model_registry.py     # ModelRegistry + ModelCapability
├── utils/
│   └── image.py              # Image processing utilities
├── config.py                 # Pydantic Settings
└── main.py                   # FastAPI entry point
```

---

## 11. Naming Conventions

| Item | Convention | Example |
|---|---|---|
| Files | snake_case | `model_registry.py` |
| Classes | PascalCase | `GeneratorService` |
| Functions | snake_case | `get_model_registry` |
| Constants | UPPER_SNAKE | `MAX_IMAGE_SIZE` |
| Endpoints | lowercase `/noun` | `/generate`, `/models` |
| Provider names | lowercase string | `"ollama"`, `"gemini"` |

---

## 12. Testing & Verification

- **Virtual Environment**: Semua AI agent HARUS menjalankan app testing dan verifikasi menggunakan Python dari dalam virtual environment (`.\venv\Scripts\python` atau `.\venv\Scripts\pytest`).
- Setiap task memiliki verification script (runnable `python -c "..."` command).
- Test error scenarios: provider not found, model not found, capability error, timeout.
- Regression: pastikan existing endpoints tetap berfungsi setelah setiap perubahan.

---

## 13. Current Version Snapshot (WAJIB UPDATE)

> **Setiap kali ada perubahan kode yang mempengaruhi fitur, struktur, endpoint, atau arsitektur:**

AI agent dan contributor **WAJIB** memperbarui file berikut:

- `plan/current_version/system_overview.md` — Update capabilities, endpoints, models, atau tech stack jika berubah.
- `plan/current_version/project_structure.md` — Update folder structure, key components, atau feature mapping jika ada file/module baru atau dihapus.

### Kapan harus update:
- ✅ Menambah/menghapus endpoint
- ✅ Menambah/menghapus provider atau model
- ✅ Menambah/menghapus service, schema, atau module
- ✅ Mengubah arsitektur atau flow request
- ✅ Menambah dependency baru di `requirements.txt`
- ✅ Menaikkan versi aplikasi (`APP_VERSION`)

### Kapan TIDAK perlu update:
- ❌ Bug fix kecil yang tidak mengubah behavior
- ❌ Refactor internal tanpa perubahan interface
- ❌ Update komentar atau dokumentasi saja

### Format update:
```
> **Snapshot Version**: beta0.X.X-nama-versi  
> **Last Updated**: YYYY-MM-DD
```

**JANGAN LUPA** — file ini adalah **snapshot realita**, bukan rencana. Hanya tulis yang sudah benar-benar diimplementasikan.
