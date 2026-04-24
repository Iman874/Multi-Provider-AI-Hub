# Foundation Core — beta0.1.1

> **Versi**: beta0.1.1  
> **Modul**: Project Scaffolding, Configuration, Error Handling, Logging  
> **Status**: 📋 Planned  
> **Referensi Blueprint**: `00-overview.md`, `01-project-structure.md`, `06-config-and-env.md`, `07-error-handling.md`

---

## 1. Latar Belakang

Sebelum modul apapun bisa dikembangkan, project membutuhkan **fondasi teknis** yang solid. Tanpa scaffolding, config system, dan error handling — tidak ada satu endpoint pun yang bisa berjalan.

Modul ini adalah **prasyarat absolut** untuk semua versi berikutnya. Ia membangun "tulang punggung" yang akan digunakan oleh setiap provider, service, dan endpoint.

### Masalah yang Diselesaikan

- Belum ada project structure → developer tidak tahu harus menulis kode dimana
- Belum ada config system → tidak bisa connect ke Ollama/Gemini
- Belum ada error handling → error akan muncul sebagai 500 Internal Server Error tanpa konteks
- Belum ada logging → debugging akan sangat sulit

### Kaitan dengan Sistem

- Menjadi dasar untuk **semua modul** di beta0.1.2+
- Config system akan digunakan oleh setiap provider (Ollama URL, Gemini API key)
- Exception hierarchy akan digunakan oleh semua service dan endpoint
- Logging middleware akan otomatis mencatat setiap request

---

## 2. Tujuan

| # | Outcome | Measurable |
|---|---|---|
| 1 | Project bisa dijalankan dengan `uvicorn` | Server start tanpa error |
| 2 | Config `.env` bisa di-load | `settings.OLLAMA_BASE_URL` mengembalikan value |
| 3 | Error handling berfungsi | Custom exception menghasilkan JSON response dengan code |
| 4 | Logging aktif | Setiap request tercatat di console/file |
| 5 | Health check endpoint tersedia | `GET /health` return `{"status": "ok"}` |

---

## 3. Scope

### ✅ Yang Dikerjakan

- Membuat seluruh folder structure sesuai blueprint
- Implementasi `app/config.py` (Settings + env loading)
- Implementasi `app/core/exceptions.py` (exception hierarchy lengkap)
- Implementasi `app/core/logging.py` (loguru setup)
- Implementasi `app/core/middleware.py` (request logging)
- Implementasi `app/main.py` (FastAPI app + startup + exception handlers)
- Membuat `.env.example`, `pyproject.toml`, `requirements.txt`, `.gitignore`
- Health check endpoint `GET /health`

### ❌ Yang Tidak Dikerjakan

- Schemas (Pydantic models) → beta0.1.2
- Model Registry → beta0.1.2
- Provider implementations (Ollama/Gemini) → beta0.1.3
- Business endpoints (/generate, /stream, etc) → beta0.1.3+
- Tests (unit/integration) → akan ditambahkan bersamaan dengan modul terkait

---

## 4. Breakdown Task

### Task 1: Project Scaffolding

- [ ] Buat `pyproject.toml` dengan metadata project dan dependencies
- [ ] Buat `requirements.txt` dengan pinned versions
- [ ] Buat `.gitignore` (Python standard + .env)
- [ ] Buat `.env.example` dengan semua variabel yang dibutuhkan
- [ ] Buat folder structure lengkap:
  ```
  app/
  app/api/
  app/api/endpoints/
  app/schemas/
  app/services/
  app/providers/
  app/core/
  app/utils/
  tests/
  ```
- [ ] Buat semua `__init__.py` file

### Task 2: Configuration System

- [ ] Implementasi `app/config.py`
  - Class `Settings` extends `BaseSettings`
  - Variabel: APP_NAME, APP_VERSION, DEBUG
  - Variabel: OLLAMA_BASE_URL, OLLAMA_TIMEOUT
  - Variabel: GEMINI_API_KEY, GEMINI_TIMEOUT
  - Variabel: LOG_LEVEL, LOG_FORMAT
  - Load dari `.env` file
- [ ] Singleton pattern: `settings = Settings()`

### Task 3: Exception Hierarchy

- [ ] Implementasi `app/core/exceptions.py`
  - `AIGatewayError` (base)
  - `ProviderNotFoundError`
  - `ModelNotFoundError`
  - `ModelCapabilityError`
  - `ProviderConnectionError`
  - `ProviderTimeoutError`
  - `ProviderAPIError`
- [ ] Setiap exception punya `message` dan `code` attribute

### Task 4: Logging System

- [ ] Implementasi `app/core/logging.py`
  - Setup loguru dengan format JSON dan text
  - Konfigurasi level dari `settings.LOG_LEVEL`
  - Output ke console (dan opsional ke file)
- [ ] Fungsi `setup_logging()` yang dipanggil saat startup

### Task 5: Request Logging Middleware

- [ ] Implementasi `app/core/middleware.py`
  - Class `RequestLoggingMiddleware`
  - Log: method, path, status_code, duration_ms
  - Integrate dengan loguru

### Task 6: FastAPI App Entry Point

- [ ] Implementasi `app/main.py`
  - Create FastAPI instance dengan title, version, description
  - Register middleware (CORS + logging)
  - Register exception handlers (AIGatewayError → JSON response)
  - Startup event: log app started, validate config
  - Shutdown event: cleanup placeholder
  - Health check: `GET /health` → `{"status": "ok", "version": "..."}`

---

## 5. Design Teknis

### File Baru

| File | Layer | Fungsi |
|---|---|---|
| `pyproject.toml` | Root | Project metadata & deps |
| `requirements.txt` | Root | Pinned dependencies |
| `.env.example` | Root | Env template |
| `.gitignore` | Root | Git ignore rules |
| `app/__init__.py` | App | Package init |
| `app/main.py` | App | FastAPI entry point |
| `app/config.py` | App | Settings & env |
| `app/core/__init__.py` | Core | Package init |
| `app/core/exceptions.py` | Core | Exception classes |
| `app/core/logging.py` | Core | Loguru setup |
| `app/core/middleware.py` | Core | Request logging |

### Flow: Startup

```
1. uvicorn app.main:app
2. FastAPI instance created
3. Middleware registered (CORS, logging)
4. Exception handlers registered
5. startup event:
   - Load settings dari .env
   - Setup logging (loguru)
   - Log "AI Generative Core started on port X"
6. Health check ready: GET /health → 200
```

### Flow: Error Handling

```
Any endpoint throws AIGatewayError subclass
  → gateway_error_handler catches it
  → Maps error code → HTTP status
  → Returns JSON: { "error": "...", "code": "..." }
```

### Perubahan pada File Existing

Tidak ada — ini adalah modul pertama yang membuat semua file dari nol.

---

## 6. Dampak ke Sistem

### Bagian yang Berubah

- Seluruh project structure dibuat dari nol
- Tidak ada kode existing yang terpengaruh

### Risiko

| Risiko | Mitigasi |
|---|---|
| Versi dependency conflict | Pin versi di requirements.txt |
| .env tidak di-load | Validasi di startup event |
| Loguru format salah | Default fallback ke text format |

### Dependency ke Modul Lain

- **Tidak ada** — ini adalah modul paling dasar
- Modul ini akan menjadi **dependency** untuk semua modul selanjutnya

---

## 7. Definition of Done

- [ ] `uvicorn app.main:app --reload` berjalan tanpa error
- [ ] `GET /health` mengembalikan `{"status": "ok", "version": "1.0.0"}`
- [ ] `.env` berhasil di-load (terlihat di log startup)
- [ ] Setiap request tercatat di console (method, path, status, duration)
- [ ] Custom exception menghasilkan JSON error response yang benar
- [ ] Swagger UI tersedia di `http://localhost:8000/docs`
- [ ] Semua folder structure sesuai blueprint `01-project-structure.md`

---

## Referensi Blueprint

- [00-overview.md](../bluprint/00-overview.md) — Architecture & structure
- [01-project-structure.md](../bluprint/01-project-structure.md) — File layout
- [06-config-and-env.md](../bluprint/06-config-and-env.md) — Config design
- [07-error-handling.md](../bluprint/07-error-handling.md) — Exception hierarchy
