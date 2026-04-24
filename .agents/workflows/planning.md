# Planning Workflow — AI Generative Core

> Workflow ini menjelaskan cara mengembangkan project secara modular  
> berdasarkan versioning system yang sudah ditetapkan.

---

## Versioning System

- Format: `beta0.1.X` (incremental per modul)
- Setiap versi memiliki scope kecil dan jelas
- Maksimal 1–3 modul per versi

### Roadmap

| Version | Modul | Status |
|---|---|---|
| beta0.1.1 | Foundation Core (scaffolding, config, logging, exceptions) | 📋 Planned |
| beta0.1.2 | Schema & Model Registry (Pydantic models, ModelRegistry) | 📋 Planned |
| beta0.1.3 | Provider Abstraction & Ollama (BaseProvider, OllamaProvider, GeneratorService, POST /generate) | 📋 Planned |
| beta0.1.4 | Gemini Provider (GeminiProvider — zero-change validation) | 📋 Planned |
| beta0.1.5 | Streaming Adapter (SSE streaming, POST /stream) | 📋 Planned |
| beta0.1.6 | Embedding Endpoint (POST /embedding) | 📋 Planned |
| beta0.1.7 | Multimodal Handling (image input support) | 📋 Planned |

### Dependency Chain

```
beta0.1.1 → beta0.1.2 → beta0.1.3 → beta0.1.4 → beta0.1.5 → beta0.1.7
                                                  └──────────→ beta0.1.6
```

---

## File & Folder Structure

Setiap versi memiliki folder di `plan/`:

```
plan/
├── ROADMAP.md                              # Master roadmap
├── beta0.1.1-foundation-core/
│   ├── plan-design-foundation-core-beta0.1.1.md   # Design doc
│   ├── task1-project-scaffolding.md                # Task files
│   ├── task2-configuration-system.md
│   └── ...
├── beta0.1.2-schema-model-registry/
│   ├── plan-design-schema-model-registry-beta0.1.2.md
│   ├── task1-common-types.md
│   └── ...
└── ...
```

---

## Workflow: Membuat Plan Design Baru

### 1. Buat folder versi

```
plan/beta0.1.X-nama-modul/
```

### 2. Buat plan design document

File: `plan-design-nama-modul-beta0.1.X.md`

Struktur WAJIB:

```markdown
# Judul Modul — beta0.1.X

> **Versi**: beta0.1.X
> **Modul**: Nama modul
> **Status**: 📋 Planned
> **Dependency**: beta0.1.Y
> **Referensi Blueprint**: file blueprint terkait

## 1. Latar Belakang
## 2. Tujuan (tabel outcome + measurable)
## 3. Scope (✅ dikerjakan, ❌ tidak dikerjakan)
## 4. Breakdown Task (checklist kasar)
## 5. Design Teknis (file baru, file dimodifikasi, flow diagram)
## 6. Dampak ke Sistem (risiko, dependency)
## 7. Definition of Done (checklist akhir)
```

### 3. Pecah menjadi task files

Setiap task dalam format:

```
task1-nama-task.md
task2-nama-task.md
...
```

---

## Workflow: Membuat Task File

Setiap task file WAJIB memiliki 9 section:

```markdown
# Task N — Judul Task

> **Modul**: beta0.1.X — Nama Modul
> **Estimasi**: Low / Medium / High
> **Dependencies**: Task sebelumnya

## 1. Judul Task
## 2. Deskripsi
## 3. Tujuan Teknis
## 4. Scope (✅ / ❌)
## 5. Langkah Implementasi (step-by-step detail + kode)
## 6. Output yang Diharapkan (contoh response/behavior)
## 7. Dependencies
## 8. Acceptance Criteria (checklist)
## 9. Estimasi
```

### Aturan Task

| Aturan | Detail |
|---|---|
| Granularity | 1 task = 1 pekerjaan jelas, 1–4 jam |
| Urutan | Fundamental → advanced |
| Independensi | Setiap task bisa dikerjakan tanpa baca design doc asli |
| Verifikasi | Setiap task memiliki verification script |
| Dependencies | Dependency antar task harus eksplisit |

---

## Workflow: Mengerjakan Task

### Urutan eksekusi per versi

1. **Baca plan design** — pahami scope dan tujuan versi
2. **Kerjakan task berurutan** — task1 → task2 → ...
3. **Verifikasi setiap task** — jalankan verification script
4. **Acceptance criteria** — checklist semua terpenuhi
5. **Regression test** — pastikan task sebelumnya masih berfungsi
6. **Mark sebagai selesai** — update status di plan design

### Parallel execution

Beberapa task bisa dikerjakan parallel jika dependency graph memungkinkan:

```
# Contoh beta0.1.2:
Task 1 (types) ──┬──▶ Task 2 (requests)    # parallel
                  ├──▶ Task 3 (responses)   # parallel
                  └──▶ Task 4 (registry)

# Contoh beta0.1.5:
Task 1 (Ollama stream) ──┐
                           ├──▶ Task 3 (service) ──▶ ...
Task 2 (Gemini stream) ──┘     # parallel
```

---

## Prinsip Arsitektur

### Provider Pattern (Open/Closed Principle)

Menambah provider baru = **ZERO changes** di:
- `app/api/endpoints/*` — endpoint code
- `app/services/generator.py` — service code
- `app/schemas/*` — data contracts

Hanya perlu:
1. Buat `app/providers/new_provider.py` (implement `BaseProvider`)
2. Tambah case di `app/providers/__init__.py` (factory)
3. Tambah config di `app/config.py`
4. Register models di `ModelRegistry`

### Validation-Before-Execution

Semua validasi (provider exists, model exists, capability check) dilakukan **sebelum** memanggil provider. Ini memastikan:
- Error response memiliki status code yang benar
- Tidak ada wasted API calls ke provider
- Streaming validation terjadi sebelum SSE dimulai

### Response Normalization

Setiap provider mengembalikan format yang **berbeda**. Service layer menormalisasi ke schema standard:

```python
# Provider returns raw dict:
{"output": str, "model": str, "provider": str, "usage": dict, "metadata": dict}

# Service wraps in Pydantic:
GenerateResponse(output=..., provider=..., model=..., usage=UsageInfo(...))
```

---

## Model & Provider Reference

### Default Models

| Model | Provider | Text | Image | Embedding |
|---|---|---|---|---|
| `llama3.2` | ollama | ✅ | ❌ | ❌ |
| `llama3.2-vision` | ollama | ✅ | ✅ | ❌ |
| `qwen3-embedding:0.6b` | ollama | ❌ | ❌ | ✅ |
| `gemini-2.0-flash` | gemini | ✅ | ✅ | ❌ |
| `gemini-2.5-flash-preview-04-17` | gemini | ✅ | ✅ | ❌ |
| `text-embedding-004` | gemini | ❌ | ❌ | ✅ |

### API Endpoints

| Method | Path | Purpose | Since |
|---|---|---|---|
| GET | `/health` | Health check | beta0.1.1 |
| GET | `/api/v1/models` | List models | beta0.1.2 |
| POST | `/api/v1/generate` | Text/multimodal generation | beta0.1.3 |
| POST | `/api/v1/stream` | SSE streaming | beta0.1.5 |
| POST | `/api/v1/embedding` | Vector embedding | beta0.1.6 |

### Provider-Specific Notes

- **Ollama**: Local API, no auth needed, images as pure base64 strings
- **Gemini**: Cloud API, requires `GEMINI_API_KEY`, images via `Part.from_bytes()`
- **Gemini Embedding**: API mungkin tidak aktif — fallback ke Ollama `qwen3-embedding:0.6b`
